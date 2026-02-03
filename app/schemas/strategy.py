from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum
from app.db.models.strategy import StrategyStatus, StrategyDifficulty, StrategyType



class StrategyBase(BaseModel):
    campaign_id: int
    stra_name: Optional[str] = None
    stra_type: Optional[StrategyType] = None
    stra_priority: int = Field(1, ge=1, le=5)
    stra_difficulty: StrategyDifficulty = StrategyDifficulty.MEDIUM
    stra_content: Dict[str, Any] = {}

class StrategyCreate(StrategyBase):
    ai_agent_id: Optional[str] = None
    ai_model: Optional[str] = None
    stra_change_reason: Optional[str] = None

class StrategyUpdate(BaseModel):
    stra_name: Optional[str] = None
    stra_status: Optional[StrategyStatus] = None
    stra_type: Optional[StrategyType] = None
    stra_difficulty: Optional[StrategyDifficulty] = None
    stra_content: Optional[Dict[str, Any]] = None
    stra_is_active: Optional[bool] = None
    stra_progress_percentage: Optional[float] = Field(None, ge=0, le=100)
    stra_change_reason: Optional[str] = None
    stra_quality_score: Optional[float] = Field(None, ge=0, le=1)
    stra_feasibility_score: Optional[float] = Field(None, ge=0, le=1)

class StrategyInDB(StrategyBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    stra_version: int
    stra_status: StrategyStatus
    stra_is_active: bool
    ai_agent_id: Optional[str] = None
    ai_model: Optional[str] = None
    stra_quality_score: float = Field(ge=0, le=1)
    stra_feasibility_score: float = Field(ge=0, le=1)
    stra_roi_estimate: float
    stra_cost_estimate: float
    stra_time_estimate_days: int
    stra_progress_percentage: float = Field(ge=0, le=100)
    stra_start_date: Optional[datetime] = None
    stra_end_date: Optional[datetime] = None
    stra_created_at: datetime
    stra_updated_at: datetime
    
    # Campos adicionales
    stra_approved_at: Optional[datetime] = None
    stra_approved_by: Optional[int] = None
    stra_rejected_at: Optional[datetime] = None
    stra_rejected_reason: Optional[str] = None
    stra_canceled_at: Optional[datetime] = None
    stra_canceled_reason: Optional[str] = None
    stra_resources_required: List[Any] = []
    stra_dependencies: List[int] = []
    stra_change_log: List[Dict[str, Any]] = []

class StrategyWithDetails(StrategyInDB):
    """Incluye información relacionada"""
    campaign_name: Optional[str] = None
    campaign_status: Optional[str] = None
    industry_name: Optional[str] = None
    
    @property
    def type_display(self) -> str:
        type_map = {
            "content": "Contenido",
            "social_media": "Redes Sociales",
            "email": "Email Marketing",
            "ads": "Publicidad Pagada",
            "seo": "SEO",
            "affiliate": "Afiliados",
            "influencer": "Influencers",
            "pr": "Relaciones Públicas",
            "event": "Eventos",
            "other": "Otro"
        }
        return type_map.get(self.stra_type.value if self.stra_type else "", "Sin tipo")
    
    @property
    def status_display(self) -> str:
        status_map = {
            "D": "Borrador",
            "P": "En Revisión",
            "A": "Aprobada",
            "R": "Rechazada",
            "C": "Cancelada"
        }
        return status_map.get(self.stra_status.value, self.stra_status.value)