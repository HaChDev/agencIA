"""
AgencIA - Schemas de Agentes
============================
Schemas Pydantic para validación de agentes IA.
"""

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.db.models.agent import AgentType


class AgentBase(BaseModel):
    """Schema base para agentes."""

    agent_name: str = Field(..., min_length=1, max_length=100)
    agent_type: AgentType
    agent_description: Optional[str] = None
    model_name: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, gt=0)
    is_active: bool = True
    capabilities: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentCreate(AgentBase):
    """Schema para crear un agente."""

    pass


class AgentUpdate(BaseModel):
    """Schema para actualizar un agente."""

    agent_name: Optional[str] = Field(None, min_length=1, max_length=100)
    agent_type: Optional[AgentType] = None
    agent_description: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    capabilities: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class AgentInDB(AgentBase):
    """Schema para agente en base de datos."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class AgentWithStrategies(AgentInDB):
    """Schema que incluye las estrategias del agente."""

    strategies_count: Optional[int] = 0

    @property
    def type_display(self) -> str:
        """Devuelve el tipo de agente en formato legible."""
        type_map = {
            AgentType.DIRECTOR: "Director",
            AgentType.CREATIVE: "Creativo",
            AgentType.ANALYST: "Analista",
            AgentType.RESEARCHER: "Investigador",
            AgentType.EXECUTOR: "Ejecutor",
            AgentType.SUPPORT: "Soporte",
        }
        return type_map.get(self.agent_type, self.agent_type.value)

    @property
    def is_available(self) -> bool:
        """Devuelve si el agente está disponible para uso."""
        return self.is_active


class AgentListResponse(BaseModel):
    """Respuesta para listar agentes."""

    agents: List[AgentInDB]
    total: int
    active_count: int
