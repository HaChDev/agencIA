"""
AgencIA - Estado del Agente Director
======================================
Definición del estado para el grafo LangGraph (Nivel Experto).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, TypedDict, Union
from uuid import uuid4

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentPhase(str, Enum):
    """Fases del workflow del agente director."""
    INITIAL = "initial"
    ANALYZING_BRIEF = "analyzing_brief"
    DIAGNOSTIC_RESEARCH = "diagnostic_research"
    DRAFTING_STRATEGY = "drafting_strategy"
    CRITIQUING_STRATEGY = "critiquing_strategy"
    REFINING_STRATEGY = "refining_strategy"
    DECOMPOSING_TASKS = "decomposing_tasks"
    ASSIGNING_AGENTS = "assigning_agents"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ReviewComment:
    """Comentario de revisión crítica."""
    aspect: str  # e.g., "Viabilidad", "Coherencia", "ROI"
    severity: str  # "low", "medium", "high", "critical"
    comment: str
    recommendation: str

@dataclass
class StrategyVersion:
    """Versión de una estrategia."""
    version_number: int
    content: dict
    critique_comments: List[ReviewComment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DirectorState(TypedDict):
    """
    Estado principal del Agente Director para LangGraph.
    Incluye historial de versiones para permitir refinamiento iterativo.
    """
    # Mensajes conversacionales (acumulativos)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Identificadores de sesión
    session_id: str
    client_id: str
    
    # Brief del cliente (entrada principal)
    client_brief: Optional[Dict]
    
    # Contexto acumulado (RAG + Research)
    research_data: Dict[str, Any]
    
    # Estrategia en desarrollo
    current_strategy: Optional[Dict]
    
    # Versiones anteriores (para tracking de mejoras)
    strategy_versions: List[StrategyVersion]
    
    # Crítica actual
    current_critique: Optional[List[ReviewComment]]
    
    # Tareas y asignaciones
    tasks: List[Dict]
    agent_assignments: Dict[str, Dict]
    
    # Control de flujo
    current_phase: str
    iteration_count: int  # Para evitar bucles infinitos de refinamiento
    
    # Errores
    errors: List[str]


def create_initial_state(
    session_id: str,
    client_id: str,
    brief: Optional[Dict] = None
) -> DirectorState:
    """
    Crea un estado inicial vacío para el Director.
    """
    return DirectorState(
        messages=[],
        session_id=session_id,
        client_id=client_id,
        client_brief=brief,
        research_data={},
        current_strategy=None,
        strategy_versions=[],
        current_critique=None,
        tasks=[],
        agent_assignments={},
        current_phase=AgentPhase.INITIAL.value,
        iteration_count=0,
        errors=[]
    )
