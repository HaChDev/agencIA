"""
AgencIA - Agente Director de Estrategia
======================================
Clase principal que encapsula el grafo y gestiona estado persistente.
"""

from typing import Dict, Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.core.memory import get_redis_checkpointer
from app.agents.director.state import create_initial_state
from app.agents.director.graph import get_director_graph

# Integración DB y Schemas
from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.strategy_repo import StrategyRepository
from app.schemas.strategy import StrategyCreate
from app.db.models.strategy import StrategyDifficulty

# Importar SessionLocal COMPARTIDO para evitar múltiples pools
from app.infrastructure.postgres.database import SessionLocal


def _is_session_active(session: AsyncSession) -> bool:
    """
    Verifica si la sesión de DB está activa y tiene conexión válida.

    Returns:
        True si la sesión está operativa, False si está cerrada.
    """
    try:
        return not session.is_closed
    except Exception:
        return False


class DirectorAgent:
    """
    Controlador principal del Director.
    Expone métodos de alto nivel para interactuar con el grafo LangGraph.
    """

    def __init__(self):
        self.graph = get_director_graph()

    async def process_campaign(
        self, campaign_id: str | int, db_session: Optional["AsyncSession"] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Ejecuta la estrategia para una campaña existente en DB.

        El agente puede aceptar una sesión existente (db_session) o crear su propia sesión.
        Se reutiliza el SessionLocal global de la aplicación para evitar crear múltiples pools.
        """
        # Validar ID Numérico
        try:
            campaign_db_id = int(campaign_id)
        except ValueError:
            yield {"error": "Invalid Campaign ID format (must be integer)"}
            return

        # Determinar si usamos la sesión proporcionada o creamos una nueva
        use_external_session = db_session is not None and _is_session_active(db_session)

        # ================================================================
        # GESTIÓN SEGURA DEL CICLO DE VIDA DE LA SESIÓN
        # ================================================================

        if use_external_session:
            # Usar la sesión proporcionada por FastAPI (el ciclo de vida lo maneja FastAPI)
            async for result in self._execute_campaign(campaign_db_id, db_session):
                yield result
        else:
            # Crear nuestra propia sesión y gestionar su ciclo de vida
            async with SessionLocal() as agent_session:
                async for result in self._execute_campaign(
                    campaign_db_id, agent_session
                ):
                    yield result

    async def _execute_campaign(
        self,
        campaign_db_id: int,
        agent_session: AsyncSession,
    ) -> AsyncGenerator[Dict, None]:
        """
        Corazón de la ejecución del agente.
        """
        try:
            # 1. Cargar Contexto de DB
            campaign_repo = CampaignRepository(agent_session)
            campaign = await campaign_repo.get_by_id(campaign_db_id)

            if not campaign:
                yield {"error": f"Campaign {campaign_db_id} not found in DB"}
                return

            # Visual feedback
            yield {
                "event": "context_loaded",
                "campaign": campaign.camp_name,
                "client": campaign.user.user_fullname if campaign.user else "Unknown",
                "status": "loaded_from_postgres",
            }

            # COMMIT para liberar la conexión y cerrar la transacción antes
            # de iniciar la ejecución larga del LangGraph. Así evitamos
            # un Timeout por inactividad ("idle in transaction") en Postgres
            await agent_session.commit()

            # 2. Configurar Memoria de Trabajo (Redis) con Namespace 'director'
            checkpointer = await get_redis_checkpointer(namespace="director")
            config = {
                "configurable": {
                    "thread_id": str(campaign.id),
                    "user_id": str(campaign.user_id),
                    "campaign_id": str(campaign.id),
                }
            }

            # Estado Inicial Híbrido: Datos de DB + Estado vacío de grafo
            initial_state = create_initial_state(
                session_id=str(campaign.id),
                client_id=str(campaign.user_id),
                brief=campaign.camp_brief_data,
            )

            # 3. Ejecutar Grafo (Thinking Loop)
            final_strategy = None

            try:
                try:
                    from rich.console import Console
                    from rich.panel import Panel
                    console = Console()
                except ImportError:
                    console = None

                async for event in self.graph.astream(initial_state, config=config):
                    yield event

                    # Interceptación de Resultados y Logging Visual
                    for node_name, node_data in event.items():
                        # ========= Logging por Consola =========
                        if console:
                            console.print(Panel(
                                f"[bold green]Node Executed:[/bold green] {node_name}\n[bold blue]Data Keys:[/bold blue] {list(node_data.keys())}",
                                title="LangGraph Execution Step",
                                expand=False
                            ))
                        else:
                            print(f"\n[LangGraph] Node Executed: {node_name} | Keys: {list(node_data.keys())}")

                        if "messages" in node_data and node_data["messages"]:
                            last_msg = node_data["messages"][-1]
                            if hasattr(last_msg, "content"):
                                preview = str(last_msg.content)[:150].replace('\n', ' ') + "..."
                                if console:
                                    console.print(f"[dim]Output Preview:[/dim] {preview}")
                                else:
                                    print(f"   -> Output Preview: {preview}")
                        # =======================================

                        if (
                            "current_strategy" in node_data
                            and node_data["current_strategy"]
                        ):
                            final_strategy = node_data["current_strategy"]
            except Exception as e:
                yield {"error": f"Graph execution failed: {str(e)}"}
                return

            # 4. Guardar la estrategia
            if final_strategy:
                try:
                    # Verificar que la sesión sigue activa antes de persistir
                    if not _is_session_active(agent_session):
                        yield {
                            "error": "Database session closed before strategy persistence"
                        }
                        return

                    strategy_repo = StrategyRepository(agent_session)
                    strategy_data = StrategyCreate(
                        campaign_id=campaign.id,
                        stra_content=final_strategy,
                        ai_agent_id="director_agent",
                        stra_name=f"Estrategia {campaign.camp_name}",
                        stra_priority=1,
                        stra_difficulty=StrategyDifficulty.MEDIUM,
                    )
                    saved_strat = await strategy_repo.save_strategy_version(
                        strategy_data
                    )

                    # Commit explícito
                    await agent_session.commit()

                    yield {
                        "event": "strategy_persisted",
                        "version": saved_strat.stra_version,
                        "db_id": str(saved_strat.id),
                    }
                except SQLAlchemyError as e:
                    # Rollback SEGURO - solo si la sesión está activa
                    if _is_session_active(agent_session):
                        try:
                            await agent_session.rollback()
                        except Exception as rb_error:
                            print(f"Warning: Rollback failed: {rb_error}")
                    yield {"error": f"Failed to persist strategy: {str(e)}"}

        except Exception as e:
            yield {"error": f"Agent execution failed: {str(e)}"}


# Singleton helper
_director = None


def get_director_agent():
    global _director
    if _director is None:
        _director = DirectorAgent()
    return _director
