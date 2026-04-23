"""
AgencIA - Agent Repository
==========================
Repositorio para la tabla de agentes IA.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent import Agent, AgentType
from app.db.repositories.base import BaseRepository


class AgentRepository(BaseRepository):
    """
    Repositorio para gestionar agentes IA del sistema.
    Proporciona métodos para CRUD y búsquedas especializadas.
    """

    async def get_by_id(self, agent_id: int) -> Optional[Agent]:
        """
        Obtiene un agente por su ID.

        Args:
            agent_id: ID del agente a buscar.

        Returns:
            El agente encontrado o None si no existe.
        """
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, agent_name: str) -> Optional[Agent]:
        """
        Obtiene un agente por su nombre único.

        Args:
            agent_name: Nombre único del agente.

        Returns:
            El agente encontrado o None si no existe.
        """
        stmt = select(Agent).where(Agent.agent_name == agent_name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_type(self, agent_type: AgentType) -> List[Agent]:
        """
        Obtiene todos los agentes de un tipo específico.

        Args:
            agent_type: Tipo de agente a buscar.

        Returns:
            Lista de agentes del tipo especificado.
        """
        stmt = select(Agent).where(Agent.agent_type == agent_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_agents(self) -> List[Agent]:
        """
        Obtiene todos los agentes activos.

        Returns:
            Lista de agentes activos.
        """
        stmt = select(Agent).where(Agent.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self) -> List[Agent]:
        """
        Obtiene todos los agentes.

        Returns:
            Lista de todos los agentes.
        """
        stmt = select(Agent).order_by(Agent.agent_type, Agent.agent_name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        agent_name: str,
        agent_type: AgentType,
        agent_description: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        capabilities: Optional[List[str]] = None,
        config: Optional[dict] = None,
    ) -> Agent:
        """
        Crea un nuevo agente en la base de datos.

        Args:
            agent_name: Nombre único del agente.
            agent_type: Tipo de agente.
            agent_description: Descripción opcional.
            model_name: Modelo LLM opcional.
            temperature: Temperatura default.
            max_tokens: Máximo de tokens.
            capabilities: Lista de capacidades.
            config: Configuración adicional.

        Returns:
            El agente creado.
        """
        agent = Agent(
            agent_name=agent_name,
            agent_type=agent_type,
            agent_description=agent_description,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            capabilities=capabilities or [],
            config=config or {},
        )

        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)

        return agent

    async def update(self, agent: Agent) -> Agent:
        """
        Actualiza un agente existente.

        Args:
            agent: Instancia del agente a actualizar.

        Returns:
            El agente actualizado.
        """
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def delete(self, agent: Agent) -> None:
        """
        Elimina un agente de la base de datos.

        Args:
            agent: Instancia del agente a eliminar.
        """
        await self.session.delete(agent)
        await self.session.commit()

    async def deactivate(self, agent_id: int) -> Optional[Agent]:
        """
        Desactiva un agente (soft delete).

        Args:
            agent_id: ID del agente a desactivar.

        Returns:
            El agente desactivado o None si no existe.
        """
        agent = await self.get_by_id(agent_id)
        if agent:
            agent.deactivate()
            await self.session.commit()
            await self.session.refresh(agent)
        return agent

    async def activate(self, agent_id: int) -> Optional[Agent]:
        """
        Activa un agente.

        Args:
            agent_id: ID del agente a activar.

        Returns:
            El agente activado o None si no existe.
        """
        agent = await self.get_by_id(agent_id)
        if agent:
            agent.activate()
            await self.session.commit()
            await self.session.refresh(agent)
        return agent

    async def add_capability(self, agent_id: int, capability: str) -> Optional[Agent]:
        """
        Agrega una capacidad a un agente.

        Args:
            agent_id: ID del agente.
            capability: Capacidad a agregar.

        Returns:
            El agente actualizado o None si no existe.
        """
        agent = await self.get_by_id(agent_id)
        if agent:
            agent.add_capability(capability)
            await self.session.commit()
            await self.session.refresh(agent)
        return agent

    async def remove_capability(
        self, agent_id: int, capability: str
    ) -> Optional[Agent]:
        """
        Elimina una capacidad de un agente.

        Args:
            agent_id: ID del agente.
            capability: Capacidad a eliminar.

        Returns:
            El agente actualizado o None si no existe.
        """
        agent = await self.get_by_id(agent_id)
        if agent:
            agent.remove_capability(capability)
            await self.session.commit()
            await self.session.refresh(agent)
        return agent

    async def get_or_create_default_agents(self) -> List[Agent]:
        """
        Obtiene o crea los agentes iniciales del sistema.
        Se usa para inicializar la tabla con los agentes base.

        Returns:
            Lista de agentes del sistema.
        """
        default_agents = [
            {
                "agent_name": "director_agent",
                "agent_type": AgentType.DIRECTOR,
                "agent_description": "Agente principal que genera estrategias de marketing basadas en el brief del cliente",
                "model_name": "llama-3.1-70b-versatile",
                "temperature": 0.7,
                "max_tokens": 4096,
                "capabilities": [
                    "strategy_generation",
                    "brief_analysis",
                    "campaign_planning",
                ],
            },
            {
                "agent_name": "creative_agent",
                "agent_type": AgentType.CREATIVE,
                "agent_description": "Agente especializado en generar contenido creativo y copy para campañas",
                "model_name": "llama-3.1-70b-versatile",
                "temperature": 0.8,
                "max_tokens": 2048,
                "capabilities": ["content_generation", "copywriting", "visual_ideas"],
            },
            {
                "agent_name": "analyst_agent",
                "agent_type": AgentType.ANALYST,
                "agent_description": "Agente de análisis de datos y métricas de campañas",
                "model_name": "llama-3.1-70b-versatile",
                "temperature": 0.3,
                "max_tokens": 4096,
                "capabilities": ["data_analysis", "metrics", "reporting"],
            },
            {
                "agent_name": "research_agent",
                "agent_type": AgentType.RESEARCHER,
                "agent_description": "Agente de investigación de mercado y competencia",
                "model_name": "llama-3.1-70b-versatile",
                "temperature": 0.5,
                "max_tokens": 4096,
                "capabilities": ["market_research", "competitor_analysis", "trends"],
            },
        ]

        created_agents = []
        for agent_data in default_agents:
            existing = await self.get_by_name(agent_data["agent_name"])
            if not existing:
                agent = await self.create(**agent_data)
                created_agents.append(agent)
            else:
                created_agents.append(existing)

        return created_agents
