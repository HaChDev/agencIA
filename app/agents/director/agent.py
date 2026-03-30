"""
AgencIA - Agente Director de Estrategia
========================================
Clase principal que encapsula el grafo y gestiona estado persistente.
"""

from typing import Dict, Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.memory import get_redis_checkpointer
from app.agents.director.state import create_initial_state
from app.agents.director.graph import get_director_graph

# Integración DB y Schemas
from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.strategy_repo import StrategyRepository
from app.schemas.strategy import StrategyCreate

class DirectorAgent:
    """
    Controlador principal del Director.
    Expone métodos de alto nivel para interactuar con el grafo LangGraph.
    """
    
    def __init__(self):
        self.graph = get_director_graph()
        
    async def process_campaign(self, campaign_id: str | int, db_session: "AsyncSession") -> AsyncGenerator[Dict, None]:
        """
        Ejecuta la estrategia para una campaña existente en DB.
        Requiere una sesión de DB activa inyectada (Dependency Injection).
        """
        # Validar ID Numérico
        try:
            campaign_db_id = int(campaign_id)
        except ValueError:
            yield {"error": "Invalid Campaign ID format (must be integer)"}
            return
            
        if not db_session:
            yield {"error": "Database session is required"}
            return

        # 1. Cargar Contexto de DB usando la sesión inyectada
        campaign_repo = CampaignRepository(db_session)
        campaign = await campaign_repo.get_by_id(campaign_db_id)
        
        if not campaign:
            yield {"error": f"Campaign {campaign_db_id} not found in DB"}
            return
            
        # Visual feedback
        yield {
            "event": "context_loaded",
            "campaign": campaign.camp_name, 
            "client": campaign.user.user_fullname if campaign.user else "Unknown",
            "status": "loaded_from_postgres"
        }

        # 2. Configurar Memoria de Trabajo (Redis) con Namespace 'director'
        # Usamos el ID de campaña como thread_id para consistencia total
        checkpointer = await get_redis_checkpointer(namespace="director")
        config = {"configurable": {"thread_id": str(campaign.id)}}
        
        # Estado Inicial Híbrido: Datos de DB + Estado vacío de grafo
        # Si ya existe estado en Redis, LangGraph lo usará automáticamente en lugar de este
        initial_state = create_initial_state(
            session_id=str(campaign.id),
            client_id=str(campaign.user_id),
            brief=campaign.camp_brief_data # El brief viene de la DB
        )

        # 3. Ejecutar Grafo (Thinking Loop)
        async for event in self.graph.astream(initial_state, config=config, checkpointer=checkpointer):
            yield event
            
            # 4. Interceptación de Resultados (Persistencia Híbrida)
            # Si el evento contiene una estrategia generada, la guardamos en SQL
            for node_name, node_data in event.items():
                if "current_strategy" in node_data and node_data["current_strategy"]:
                    # Guardar versión en DB usando la misma sesión
                    strategy_repo = StrategyRepository(db_session)
                    strategy_data = StrategyCreate(
                        campaign_id=campaign.id,
                        stra_content=node_data["current_strategy"],
                        ai_agent_id="director_agent",
                        stra_name=f"Estrategia {campaign.camp_name}"
                    )
                    saved_strat = await strategy_repo.save_strategy_version(strategy_data)
                    yield {
                        "event": "strategy_persisted", 
                        "version": saved_strat.stra_version, 
                        "db_id": str(saved_strat.id)
                    }

# Singleton helper
_director = None
def get_director_agent():
    global _director
    if _director is None:
        _director = DirectorAgent()
    return _director
