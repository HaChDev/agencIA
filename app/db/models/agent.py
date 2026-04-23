"""
AgencIA - Modelo de Agentes
===========================
Definición de tabla para Agentes IA del sistema.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import enum

from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Boolean,
    Float,
    DateTime,
    JSON,
    CheckConstraint,
    ForeignKey,
    DECIMAL,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import Identity

from app.db.base import Base


# Enums para los campos con opciones limitadas
class AgentType(str, enum.Enum):
    """Tipos de agentes IA del sistema AgencIA."""
    DIRECTOR = "DIRECTOR"
    DIAGNOSTIC = "DIAGNOSTIC"
    CREATIVE = "CREATIVE"
    ADS_MANAGER = "ADS_MANAGER"
    CUSTOMER_ENGAGEMENT = "CUSTOMER_ENGAGEMENT"
    SEO_SPECIALIST = "SEO_SPECIALIST"
    SOCIAL_MONITOR = "SOCIAL_MONITOR"
    EMAIL_MARKETING = "EMAIL_MARKETING"


class Agent(Base):
    """
    Agentes IA del sistema AgencIA.
    Cada agente representa un rol especializado con su propia configuración.
    """

    __tablename__ = "agents"

    # ID principal
    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=9223372036854775807,
            cache=1,
            cycle=False,
        ),
        primary_key=True,
    )

    # Información básica del agente
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Nombre único del agente (ej: director_agent)",
    )
    agent_type: Mapped[AgentType] = mapped_column(
        String(50),
        nullable=False,
        comment="Tipo de agente: DIRECTOR, CREATIVE, ANALYST, etc.",
    )
    agent_description: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="Descripción de las funciones del agente"
    )

    # Configuración del modelo LLM
    model_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Modelo LLM usado por defecto"
    )
    temperature: Mapped[float] = mapped_column(
        DECIMAL(3, 2),
        default=0.7,
        nullable=False,
        comment="Temperatura default (0.0-1.0)",
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, default=4096, nullable=False, comment="Máximo de tokens por solicitud"
    )

    # Estado del agente
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Si el agente está activo"
    )

    # Configuración flexible
    capabilities: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Array de capacidades/herramientas del agente",
    )
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Configuración específica del agente",
    )

    # Timestamps automáticos
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    ################################################### Relaciones #######################################################

    strategies: Mapped[List["Strategy"]] = relationship(back_populates="agent")

    ################################################### Constraints #######################################################

    __table_args__ = (
        # Check constraint para agent_type
        CheckConstraint(
            "agent_type IN ('DIRECTOR', 'DIAGNOSTIC', 'CREATIVE', 'ADS_MANAGER', 'CUSTOMER_ENGAGEMENT', 'SEO_SPECIALIST', 'SOCIAL_MONITOR', 'EMAIL_MARKETING')",
            name="check_agent_type",
        ),
        # Check constraint para temperature
        CheckConstraint(
            "temperature BETWEEN 0.0 AND 1.0", name="check_temperature_range"
        ),
        # Check constraint para max_tokens
        CheckConstraint("max_tokens > 0", name="check_max_tokens_positive"),
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.agent_name}', type='{self.agent_type.value}')>"

    # Propiedades útiles
    @property
    def is_available(self) -> bool:
        """Devuelve si el agente está disponible para uso"""
        return self.is_active

    @property
    def type_display(self) -> str:
        """Devuelve el tipo de agente en formato legible"""
        type_map = {
            AgentType.DIRECTOR: "Director de Estrategia",
            AgentType.DIAGNOSTIC: "Diagnóstico Inicial",
            AgentType.CREATIVE: "Creador de Contenido",
            AgentType.ADS_MANAGER: "Publicidad Digital",
            AgentType.CUSTOMER_ENGAGEMENT: "Atención al Cliente",
            AgentType.SEO_SPECIALIST: "Especialista SEO",
            AgentType.SOCIAL_MONITOR: "Gestión Social",
            AgentType.EMAIL_MARKETING: "Email Marketing",
        }
        return type_map.get(self.agent_type, self.agent_type.value)

    @property
    def capabilities_list(self) -> List[str]:
        """Devuelve las capacidades como lista"""
        if isinstance(self.capabilities, list):
            return self.capabilities
        return []

    def add_capability(self, capability: str) -> None:
        """Agrega una capacidad al agente"""
        caps = self.capabilities_list
        if capability not in caps:
            caps.append(capability)
            self.capabilities = caps

    def remove_capability(self, capability: str) -> None:
        """Elimina una capacidad del agente"""
        caps = self.capabilities_list
        if capability in caps:
            caps.remove(capability)
            self.capabilities = caps

    def deactivate(self) -> None:
        """Desactiva el agente"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activa el agente"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def update_config(self, key: str, value: Any) -> None:
        """Actualiza una configuración específica"""
        current_config = self.config if isinstance(self.config, dict) else {}
        current_config[key] = value
        self.config = current_config
        self.updated_at = datetime.utcnow()
