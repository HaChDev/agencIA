from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, BigInteger, Integer, String, Boolean, Float, DateTime, JSON, CheckConstraint, ForeignKey, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Identity
import enum

Base = declarative_base()

# Enums para los campos con opciones limitadas
class StrategyStatus(enum.Enum):
    DRAFT = "D"
    PENDING = "P"
    APPROVED = "A"
    REJECTED = "R"
    CANCELLED = "C"

class StrategyDifficulty(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXPERT = "EXPERT"

class StrategyType(enum.Enum):
    CONTENT = "content"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    ADS = "ads"
    SEO = "seo"
    AFFILIATE = "affiliate"
    INFLUENCER = "influencer"
    PR = "pr"
    EVENT = "event"
    OTHER = "other"

class Strategy(Base):
    """
    Estrategias aprobadas y sus versiones para campañas de marketing.
    Control de versiones y recuperación de acciones de agentes IA.
    """
    __tablename__ = "strategies"
    
    # ID principal
    id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cache=1, cycle=False), primary_key=True)
    
    # Relación con la campaña
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    
    # Información de versión y estado
    stra_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    stra_status: Mapped[str] = mapped_column(String(1), default=StrategyStatus.DRAFT.value, nullable=False, comment="Estado: D=Draft/Borrador, P=Pending/En revisión, A=Approved/Aprobada, R=Rejected/Rechazada, C=Canceled/Cancelada")
    
    # Contenido de la estrategia
    stra_content: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False, comment="Estructura completa de la estrategia en JSON (generada por IA)")
    
    # Bandera de activa
    stra_is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Auditoría y control
    stra_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stra_approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, comment="Usuario que aprobó")
    stra_rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stra_rejected_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Razón del rechazo")
    stra_canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stra_canceled_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Razón de cancelación")
    
    # Metadata de la estrategia
    stra_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Nombre descriptivo de la estrategia")
    stra_type: Mapped[Optional[StrategyType]] = mapped_column(Enum(StrategyType), nullable=True, comment="Tipo de estrategia")
    stra_priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="1=Alta, 5=Baja")
    stra_difficulty: Mapped[str] = mapped_column(String(20), default=StrategyDifficulty.MEDIUM.value, nullable=False, comment="Dificultad: LOW, MEDIUM, HIGH, EXPERT")

    # Información del agente IA
    ai_agent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="ID del agente IA que generó esta versión")
    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Modelo de IA usado (ej: 'gpt-4', 'claude-3', etc.)")
    ai_temperature: Mapped[Optional[float]] = mapped_column(DECIMAL(3, 2), default=0.7, nullable=True, comment="Temperatura usada en generación")
    ai_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Tokens consumidos")
    ai_generation_time: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Tiempo en segundos")
    
    # Puntajes y evaluaciones
    stra_quality_score: Mapped[float] = mapped_column(DECIMAL(3, 2), default=0.0, nullable=False, comment="Puntaje de calidad (0.0-1.0)")
    stra_feasibility_score: Mapped[float] = mapped_column(DECIMAL(3, 2), default=0.0, nullable=False, comment="Puntaje de factibilidad (0.0-1.0)")
    stra_roi_estimate: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0, nullable=False, comment="ROI estimado en porcentaje")
    stra_cost_estimate: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.0, nullable=False, comment="Costo estimado de implementación")
    stra_time_estimate_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False, comment="Tiempo estimado en días")
    
    # Campos de timeline y seguimiento
    stra_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stra_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    stra_progress_percentage: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0, nullable=False, comment="Porcentaje de progreso de implementación (0-100)")
    
    # Recursos y dependencias
    stra_resources_required: Mapped[List[Any]] = mapped_column(JSONB, default=list, nullable=False, comment="Recursos necesarios para implementar la estrategia")
    stra_dependencies: Mapped[List[int]] = mapped_column(JSONB, default=list, nullable=False, comment="IDs de otras estrategias de las que depende")
    
    # Control de cambios y versionado
    stra_change_log: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False, comment="Historial de cambios en formato JSON para auditoría y rollback")
    stra_change_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Razón del cambio en esta versión")
    
    # Timestamps automáticos
    stra_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    stra_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    ################################################### Relaciones  #######################################################

    campaign: Mapped["Campaign"] = relationship(back_populates="strategies")
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    approved_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[stra_approved_by], backref="approved_strategies")
    
    ################################################### Constraints adicionales (se pueden definir en __table_args__) ##################################################

    __table_args__ = (
        # Check constraint para stra_status
        CheckConstraint("stra_status IN ('D', 'P', 'A', 'R', 'C')", name="check_strategy_status"),
        
        # Check constraint para stra_priority
        CheckConstraint("stra_priority BETWEEN 1 AND 5", name="check_strategy_priority"),
        
        # Check constraint para stra_difficulty
        CheckConstraint("stra_difficulty IN ('LOW', 'MEDIUM', 'HIGH', 'EXPERT')", name="check_strategy_difficulty"),
        
        # Check constraint para stra_quality_score
        CheckConstraint("stra_quality_score BETWEEN 0.0 AND 1.0", name="check_quality_score_range"),
        
        # Check constraint para stra_feasibility_score
        CheckConstraint("stra_feasibility_score BETWEEN 0.0 AND 1.0", name="check_feasibility_score_range"),
        
        # Check constraint para stra_progress_percentage
        CheckConstraint("stra_progress_percentage BETWEEN 0.0 AND 100.0", name="check_progress_percentage_range"),
        
        # Check constraint para stra_version
        CheckConstraint("stra_version > 0", name="check_version_positive"),
        
        # Check constraint para fechas lógicas
        CheckConstraint("""(stra_start_date IS NULL OR stra_end_date IS NULL) OR (stra_start_date <= stra_end_date)""", name="check_dates_logic"),
    )
    
    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name='{self.stra_name}', version={self.stra_version}, status='{self.stra_status.value}')>"
    
    # Propiedades útiles
    @property
    def is_draft(self) -> bool:
        return self.stra_status == StrategyStatus.DRAFT
    
    @property
    def is_approved(self) -> bool:
        return self.stra_status == StrategyStatus.APPROVED
    
    @property
    def is_active(self) -> bool:
        return self.stra_is_active
    
    @property
    def days_remaining(self) -> Optional[int]:
        """Días restantes para completar la estrategia"""
        if self.stra_end_date and self.stra_progress_percentage < 100:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if self.stra_end_date > now:
                return (self.stra_end_date - now).days
        return None
    
    @property
    def type_display(self) -> str:
        """Devuelve el tipo de estrategia en formato legible"""
        if not self.stra_type:
            return "Sin tipo"
        type_map = {
            StrategyType.CONTENT: "Contenido",
            StrategyType.SOCIAL_MEDIA: "Redes Sociales",
            StrategyType.EMAIL: "Email Marketing",
            StrategyType.ADS: "Publicidad Pagada",
            StrategyType.SEO: "SEO",
            StrategyType.AFFILIATE: "Afiliados",
            StrategyType.INFLUENCER: "Influencers",
            StrategyType.PR: "Relaciones Públicas",
            StrategyType.EVENT: "Eventos",
            StrategyType.OTHER: "Otro"
        }
        return type_map.get(self.stra_type, self.stra_type.value.title())
    
    @property
    def status_display(self) -> str:
        """Devuelve el estado en formato legible"""
        status_map = {
            StrategyStatus.DRAFT: "Borrador",
            StrategyStatus.PENDING: "En Revisión",
            StrategyStatus.APPROVED: "Aprobada",
            StrategyStatus.REJECTED: "Rechazada",
            StrategyStatus.CANCELLED: "Cancelada"
        }
        return status_map.get(self.stra_status, self.stra_status.value)
    
    @property
    def difficulty_display(self) -> str:
        """Devuelve la dificultad en formato legible"""
        difficulty_map = {
            StrategyDifficulty.LOW: "Baja",
            StrategyDifficulty.MEDIUM: "Media",
            StrategyDifficulty.HIGH: "Alta",
            StrategyDifficulty.EXPERT: "Experto"
        }
        return difficulty_map.get(self.stra_difficulty, self.stra_difficulty.value)
    
    def add_change_log(self, change_type: str, description: str, user_id: Optional[int] = None):
        """Agrega una entrada al log de cambios"""
        change_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": change_type,
            "description": description,
            "user_id": user_id,
            "ai_agent_id": self.ai_agent_id
        }
        
        # Mantener solo los últimos 50 cambios
        current_log = self.stra_change_log or []
        if len(current_log) >= 50:
            current_log = current_log[-49:]
        
        current_log.append(change_entry)
        self.stra_change_log = current_log
    
    def approve(self, approved_by: Optional[int] = None):
        """Aprueba la estrategia"""
        self.stra_status = StrategyStatus.APPROVED
        self.stra_approved_at = datetime.utcnow()
        self.stra_approved_by = approved_by
        self.add_change_log("approval", "Estrategia aprobada", approved_by)
    
    def reject(self, reason: str, rejected_by: Optional[int] = None):
        """Rechaza la estrategia"""
        self.stra_status = StrategyStatus.REJECTED
        self.stra_rejected_at = datetime.utcnow()
        self.stra_rejected_reason = reason
        self.add_change_log("rejection", f"Estrategia rechazada: {reason}", rejected_by)
    
    def cancel(self, reason: str, cancelled_by: Optional[int] = None):
        """Cancela la estrategia"""
        self.stra_status = StrategyStatus.CANCELLED
        self.stra_canceled_at = datetime.utcnow()
        self.stra_canceled_reason = reason
        self.add_change_log("cancellation", f"Estrategia cancelada: {reason}", cancelled_by)