"""
AgencIA - Modelos de Negocio
============================
Definición de tabla para Campañas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import enum

from sqlalchemy import String, DateTime, ForeignKey, Float, CheckConstraint, BigInteger, Identity, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import FetchedValue

from app.db.base import Base

# Enums para los campos con opciones limitadas
class CampaignStatus(str, enum.Enum):
    PLANNING = "P"  # Planificación
    ACTIVE = "A"    # Activa
    COMPLETED = "C" # Completada
    PAUSED = "S"    # Pausada (Suspended)
    CANCELLED = "X" # Cancelada

class CampaignPriority(int, enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class Campaign(Base):
    """
    Unidad central de trabajo (Thread de Agencia).
    """
    __tablename__ = "campaigns"
    
    # ID principal
    id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1), primary_key=True)
    
    # Relación con usuario
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Información básica
    camp_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Nombre de la campaña")
    camp_status: Mapped[CampaignStatus] = mapped_column(String(1), default=CampaignStatus.PLANNING, nullable=False, 
        comment="Estado: P=Planificación, A=Activa, C=Completada, S=Pausada, X=Cancelada")
    camp_brief_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False,
        comment="Datos del brief en formato JSON (objetivos, audiencia, etc.)"
    )
    camp_budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="Presupuesto total de la campaña")
    
    # Fechas
    camp_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="Fecha de inicio planeada")
    camp_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="Fecha de finalización planeada")

    # Calificaciones y evaluaciones
    camp_quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="Calificación de calidad (0.0-1.0)")
    camp_quality_score_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Razón de la calificación de calidad")
    camp_objective: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Objetivo principal de la campaña")
    
    # Relaciones con otras entidades
    industry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("industries.id", ondelete="SET NULL"), nullable=True, comment="ID de la industria relacionada")
    camp_dipo_ids: Mapped[List[int]] = mapped_column(JSONB, default=list, nullable=False, comment="Array de IDs de divisiones políticas donde se aplica")
    
    # Metadata adicional
    camp_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, comment="Código único de la campaña")
    camp_priority: Mapped[CampaignPriority] = mapped_column(Integer, default=CampaignPriority.LOW, nullable=False, comment="Prioridad: 1=Baja, 2=Media, 3=Alta, 4=Urgente")
    camp_progress_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="Porcentaje de progreso (0-100)")
    camp_roi_actual: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="ROI real obtenido")
    camp_spent_budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="Presupuesto gastado hasta el momento")
    camp_tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False, comment="Etiquetas para categorizar la campaña")
    
    # Auditoría y control
    camp_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    camp_approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    camp_cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    camp_cancelled_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    user: Mapped["User"] = relationship(back_populates="campaigns", foreign_keys=[user_id])
    strategies: Mapped[List["Strategy"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    industry: Mapped["Industry"] = relationship(back_populates="campaigns")
    
    # Usuario que aprobó (relación separada)
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[camp_approved_by], back_populates="approved_campaigns")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("camp_status IN ('P', 'A', 'C', 'S', 'X')", name="check_campaign_status"),
        CheckConstraint("camp_quality_score >= 0.0 AND camp_quality_score <= 1.0", name="check_campaign_quality_score"),
        CheckConstraint("camp_budget >= 0.0", name="check_campaign_budget"),
        CheckConstraint("camp_spent_budget >= 0.0", name="check_campaign_spent_budget"),
        CheckConstraint("camp_progress_percentage >= 0.0 AND camp_progress_percentage <= 100.0", name="check_campaign_progress"),
        CheckConstraint(
            """
            (camp_start_date IS NULL OR camp_end_date IS NULL) 
            OR (camp_start_date <= camp_end_date)
            """,
            name="check_campaign_dates"
        ),
        CheckConstraint("camp_spent_budget <= camp_budget", name="check_campaign_spent_vs_budget"),
        CheckConstraint("camp_priority BETWEEN 1 AND 4", name="check_campaign_priority"),
    )
    
    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.camp_name}', status='{self.camp_status.value}')>"
    
    # Propiedades útiles
    @property
    def is_active(self) -> bool:
        return self.camp_status == CampaignStatus.ACTIVE
    
    @property
    def is_planning(self) -> bool:
        return self.camp_status == CampaignStatus.PLANNING
    
    @property
    def is_completed(self) -> bool:
        return self.camp_status == CampaignStatus.COMPLETED
    
    @property
    def remaining_budget(self) -> float:
        """Presupuesto restante"""
        return max(0.0, self.camp_budget - self.camp_spent_budget)
    
    @property
    def budget_utilization(self) -> float:
        """Porcentaje de presupuesto utilizado"""
        if self.camp_budget == 0:
            return 0.0
        return min(100.0, (self.camp_spent_budget / self.camp_budget) * 100)
    
    @property
    def days_remaining(self) -> Optional[int]:
        """Días restantes para completar la campaña"""
        if self.camp_end_date and self.camp_progress_percentage < 100:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if self.camp_end_date > now:
                return (self.camp_end_date - now).days
        return None
    
    @property
    def status_display(self) -> str:
        """Devuelve el estado en formato legible"""
        status_map = {
            CampaignStatus.PLANNING: "Planificación",
            CampaignStatus.ACTIVE: "Activa",
            CampaignStatus.COMPLETED: "Completada",
            CampaignStatus.PAUSED: "Pausada",
            CampaignStatus.CANCELLED: "Cancelada"
        }
        return status_map.get(self.camp_status, self.camp_status.value)
    
    @property
    def priority_display(self) -> str:
        """Devuelve la prioridad en formato legible"""
        priority_map = {
            1: "Baja",
            2: "Media",
            3: "Alta",
            4: "Urgente"
        }
        return priority_map.get(self.camp_priority, f"Prioridad {self.camp_priority}")
    
    # Métodos de negocio
    def start(self) -> None:
        """Inicia la campaña"""
        if self.camp_status == CampaignStatus.PLANNING:
            self.camp_status = CampaignStatus.ACTIVE
            self.updated_at = datetime.utcnow()
    
    def complete(self) -> None:
        """Marca la campaña como completada"""
        if self.camp_status == CampaignStatus.ACTIVE:
            self.camp_status = CampaignStatus.COMPLETED
            self.camp_progress_percentage = 100.0
            self.updated_at = datetime.utcnow()
    
    def pause(self) -> None:
        """Pausa la campaña"""
        if self.camp_status == CampaignStatus.ACTIVE:
            self.camp_status = CampaignStatus.PAUSED
            self.updated_at = datetime.utcnow()
    
    def resume(self) -> None:
        """Reanuda una campaña pausada"""
        if self.camp_status == CampaignStatus.PAUSED:
            self.camp_status = CampaignStatus.ACTIVE
            self.updated_at = datetime.utcnow()
    
    def cancel(self, reason: str = None, cancelled_by: int = None) -> None:
        """Cancela la campaña"""
        if self.camp_status not in [CampaignStatus.COMPLETED, CampaignStatus.CANCELLED]:
            self.camp_status = CampaignStatus.CANCELLED
            self.camp_cancelled_at = datetime.utcnow()
            self.camp_cancelled_reason = reason
            self.updated_at = datetime.utcnow()
    
    def approve(self, approved_by: int = None) -> None:
        """Aprueba la campaña"""
        self.camp_approved_at = datetime.utcnow()
        self.camp_approved_by = approved_by
        self.updated_at = datetime.utcnow()
    
    def update_progress(self, percentage: float) -> None:
        """Actualiza el porcentaje de progreso"""
        if 0.0 <= percentage <= 100.0:
            self.camp_progress_percentage = percentage
            self.updated_at = datetime.utcnow()
    
    def add_spent_budget(self, amount: float) -> None:
        """Agrega gasto al presupuesto utilizado"""
        if amount > 0:
            new_spent = self.camp_spent_budget + amount
            if new_spent <= self.camp_budget:
                self.camp_spent_budget = new_spent
                self.updated_at = datetime.utcnow()
            else:
                raise ValueError("El gasto excede el presupuesto disponible")
    
    def add_tag(self, tag: str) -> None:
        """Agrega una etiqueta a la campaña"""
        if tag and tag not in self.camp_tags:
            self.camp_tags.append(tag)
            self.updated_at = datetime.utcnow()
    
    def remove_tag(self, tag: str) -> None:
        """Elimina una etiqueta de la campaña"""
        if tag in self.camp_tags:
            self.camp_tags.remove(tag)
            self.updated_at = datetime.utcnow()