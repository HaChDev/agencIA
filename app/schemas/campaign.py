# schemas/campaign.py
from pydantic import BaseModel, ConfigDict, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum as PyEnum
from app.db.models.campaign import CampaignStatus, CampaignPriority


# Schema base
class CampaignBase(BaseModel):
    camp_name: str = Field(..., min_length=1, max_length=100)
    camp_status: CampaignStatus = CampaignStatus.PLANNING
    camp_objective: Optional[str] = Field(None, max_length=255)
    camp_budget: float = Field(0.0, ge=0.0)
    industry_id: Optional[int] = None
    camp_priority: CampaignPriority = CampaignPriority.LOW
    
    # Validadores
    @validator('camp_name')
    def validate_camp_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("El nombre de la campaña no puede estar vacío")
        return v.strip()
    
    @validator('camp_budget')
    def validate_budget(cls, v):
        if v < 0:
            raise ValueError("El presupuesto no puede ser negativo")
        return v

# Schema para crear
class CampaignCreate(CampaignBase):
    user_id: int
    camp_brief_data: Dict[str, Any] = {}
    camp_start_date: Optional[datetime] = None
    camp_end_date: Optional[datetime] = None
    camp_dipo_ids: List[int] = []
    camp_tags: List[str] = []
    
    @validator('camp_end_date')
    def validate_dates(cls, v, values):
        if 'camp_start_date' in values and v and values['camp_start_date']:
            if v < values['camp_start_date']:
                raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
        return v

# Schema para actualizar
class CampaignUpdate(BaseModel):
    camp_name: Optional[str] = Field(None, min_length=1, max_length=100)
    camp_status: Optional[CampaignStatus] = None
    camp_objective: Optional[str] = Field(None, max_length=255)
    camp_budget: Optional[float] = Field(None, ge=0.0)
    camp_priority: Optional[CampaignPriority] = None
    camp_brief_data: Optional[Dict[str, Any]] = None
    camp_start_date: Optional[datetime] = None
    camp_end_date: Optional[datetime] = None
    camp_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    camp_quality_score_reason: Optional[str] = Field(None, max_length=255)
    camp_progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    camp_spent_budget: Optional[float] = Field(None, ge=0.0)
    camp_roi_actual: Optional[float] = None
    industry_id: Optional[int] = None
    camp_dipo_ids: Optional[List[int]] = None
    camp_tags: Optional[List[str]] = None
    
    @validator('camp_end_date')
    def validate_dates(cls, v, values):
        if 'camp_start_date' in values and v and values['camp_start_date']:
            if v < values['camp_start_date']:
                raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
        return v
    
    @validator('camp_spent_budget')
    def validate_spent_budget(cls, v, values):
        if v is not None and 'camp_budget' in values and values['camp_budget'] is not None:
            if v > values['camp_budget']:
                raise ValueError("El gasto no puede exceder el presupuesto")
        return v

# Schema en la base de datos
class CampaignInDB(CampaignBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    camp_brief_data: Dict[str, Any] = {}
    camp_start_date: Optional[datetime] = None
    camp_end_date: Optional[datetime] = None
    camp_quality_score: float = Field(0.0, ge=0.0, le=1.0)
    camp_quality_score_reason: Optional[str] = None
    camp_progress_percentage: float = Field(0.0, ge=0.0, le=100.0)
    camp_spent_budget: float = Field(0.0, ge=0.0)
    camp_roi_actual: Optional[float] = None
    camp_dipo_ids: List[int] = []
    camp_tags: List[str] = []
    camp_approved_at: Optional[datetime] = None
    camp_approved_by: Optional[int] = None
    camp_cancelled_at: Optional[datetime] = None
    camp_cancelled_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Schema con relaciones (para respuestas detalladas)
class CampaignWithRelations(CampaignInDB):
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    industry_name: Optional[str] = None
    total_strategies: int = 0
    active_strategies: int = 0
    
    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.camp_budget - self.camp_spent_budget)
    
    @property
    def budget_utilization(self) -> float:
        if self.camp_budget == 0:
            return 0.0
        return min(100.0, (self.camp_spent_budget / self.camp_budget) * 100)
    
    @property
    def is_over_budget(self) -> bool:
        return self.camp_spent_budget > self.camp_budget
    
    @property
    def status_display(self) -> str:
        status_map = {
            "P": "Planificación",
            "A": "Activa",
            "C": "Completada",
            "S": "Pausada",
            "X": "Cancelada"
        }
        return status_map.get(self.camp_status.value, self.camp_status.value)
    
    @property
    def priority_display(self) -> str:
        priority_map = {
            1: "Baja",
            2: "Media",
            3: "Alta",
            4: "Urgente"
        }
        return priority_map.get(self.camp_priority.value, f"Prioridad {self.camp_priority}")

# Schema para listado (solo campos esenciales)
class CampaignList(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    camp_name: str
    camp_status: CampaignStatus
    camp_budget: float
    camp_spent_budget: float
    camp_progress_percentage: float
    camp_start_date: Optional[datetime] = None
    camp_end_date: Optional[datetime] = None
    created_at: datetime
    user_name: Optional[str] = None
    industry_name: Optional[str] = None
    
    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.camp_budget - self.camp_spent_budget)

# Schema para estadísticas
class CampaignStats(BaseModel):
    total_campaigns: int = 0
    planning_campaigns: int = 0
    active_campaigns: int = 0
    completed_campaigns: int = 0
    paused_campaigns: int = 0
    cancelled_campaigns: int = 0
    total_budget: float = 0.0
    total_spent: float = 0.0
    avg_progress: float = 0.0
    avg_quality_score: float = 0.0