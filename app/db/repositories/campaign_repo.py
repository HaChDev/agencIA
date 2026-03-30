"""
AgencIA - Campaign Repository
=============================
Repositorio completo para gestión de campañas con todas las operaciones CRUD
y métodos de negocio necesarios para el proyecto.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.campaign import Campaign, CampaignStatus, CampaignPriority
from app.db.models.user import User
from app.db.repositories.base import BaseRepository
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CampaignRepository(BaseRepository):
    """
    Repositorio robusto para gestión de campañas.
    Incluye operaciones CRUD, búsquedas avanzadas y métodos de negocio.
    """
    
    # ============================================
    # OPERACIONES CREATE
    # ============================================
    
    async def create_campaign(
        self,
        campaign_in: CampaignCreate
    ) -> Campaign:
        """
        Crea una nueva campaña validada por el schema CampaignCreate.
        """
        async def _create():
            campaign = Campaign(
                **campaign_in.model_dump()
            )
            self.session.add(campaign)
            await self.session.flush()
            return campaign
        
        return await self.execute_with_retry(_create)
    
    # ============================================
    # OPERACIONES READ
    # ============================================
    
    async def get_by_id(
        self, 
        campaign_id: int,
        load_relations: bool = True
    ) -> Optional[Campaign]:
        """
        Obtiene una campaña por ID con opción de cargar relaciones.
        
        Args:
            campaign_id: ID de la campaña
            load_relations: Si True, carga user, strategies e industry
            
        Returns:
            Campaign o None si no existe
        """
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        
        if load_relations:
            stmt = stmt.options(
                selectinload(Campaign.user),
                selectinload(Campaign.strategies),
                selectinload(Campaign.industry)
            )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_code(self, camp_code: str) -> Optional[Campaign]:
        """Obtiene una campaña por su código único."""
        stmt = select(Campaign).where(Campaign.camp_code == camp_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_by_user(
        self,
        user_id: int,
        status: Optional[CampaignStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Campaign]:
        """
        Obtiene todas las campañas de un usuario con filtros opcionales.
        
        Args:
            user_id: ID del usuario
            status: Filtro opcional por estado
            limit: Máximo de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de campañas
        """
        stmt = select(Campaign).where(Campaign.user_id == user_id)
        
        if status:
            stmt = stmt.where(Campaign.camp_status == status)
        
        stmt = stmt.order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_active_campaigns(
        self,
        user_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Campaign]:
        """Obtiene campañas activas, opcionalmente filtradas por usuario."""
        stmt = select(Campaign).where(Campaign.camp_status == CampaignStatus.ACTIVE)
        
        if user_id:
            stmt = stmt.where(Campaign.user_id == user_id)
        
        stmt = stmt.order_by(Campaign.camp_priority.desc(), Campaign.created_at.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_campaigns(
        self,
        search_term: Optional[str] = None,
        user_id: Optional[int] = None,
        status: Optional[CampaignStatus] = None,
        priority: Optional[int] = None,
        industry_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        start_date_from: Optional[datetime] = None,
        start_date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Campaign]:
        """
        Búsqueda avanzada de campañas con múltiples filtros.
        
        Args:
            search_term: Busca en nombre y objetivo
            user_id: Filtro por usuario
            status: Filtro por estado
            priority: Filtro por prioridad
            industry_id: Filtro por industria
            tags: Lista de tags (campaña debe tener al menos uno)
            min_budget: Presupuesto mínimo
            max_budget: Presupuesto máximo
            start_date_from: Fecha inicio desde
            start_date_to: Fecha inicio hasta
            limit: Máximo de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de campañas que cumplen los criterios
        """
        stmt = select(Campaign)
        
        # Filtros
        conditions = []
        
        if search_term:
            search_pattern = f"%{search_term}%"
            conditions.append(
                or_(
                    Campaign.camp_name.ilike(search_pattern),
                    Campaign.camp_objective.ilike(search_pattern)
                )
            )
        
        if user_id:
            conditions.append(Campaign.user_id == user_id)
        
        if status:
            conditions.append(Campaign.camp_status == status)
        
        if priority:
            conditions.append(Campaign.camp_priority == priority)
        
        if industry_id:
            conditions.append(Campaign.industry_id == industry_id)
        
        if tags:
            # PostgreSQL JSONB contains check
            for tag in tags:
                conditions.append(Campaign.camp_tags.contains([tag]))
        
        if min_budget is not None:
            conditions.append(Campaign.camp_budget >= min_budget)
        
        if max_budget is not None:
            conditions.append(Campaign.camp_budget <= max_budget)
        
        if start_date_from:
            conditions.append(Campaign.camp_start_date >= start_date_from)
        
        if start_date_to:
            conditions.append(Campaign.camp_start_date <= start_date_to)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(Campaign.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_by_status(self, user_id: Optional[int] = None) -> Dict[str, int]:
        """
        Cuenta campañas agrupadas por estado.
        
        Returns:
            Dict con formato: {"PLANNING": 5, "ACTIVE": 3, ...}
        """
        stmt = select(Campaign.camp_status, func.count(Campaign.id))
        
        if user_id:
            stmt = stmt.where(Campaign.user_id == user_id)
        
        stmt = stmt.group_by(Campaign.camp_status)
        
        result = await self.session.execute(stmt)
        return {status.value: count for status, count in result.all()}
    
    # ============================================
    # OPERACIONES UPDATE
    # ============================================
    
    async def update_campaign(
        self,
        campaign_id: int,
        campaign_update: CampaignUpdate
    ) -> Optional[Campaign]:
        """
        Actualiza una campaña usando el schema CampaignUpdate.
        """
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if not campaign:
            return None
        
        # Convertir schema a dict excluyendo campos no enviados
        update_data = campaign_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(campaign, field):
                setattr(campaign, field, value)
        
        campaign.updated_at = datetime.utcnow()
        await self.session.flush()
        return campaign
    
    async def update_status(
        self,
        campaign_id: int,
        new_status: CampaignStatus
    ) -> Optional[Campaign]:
        """Actualiza el estado de una campaña."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if not campaign:
            return None
        
        campaign.camp_status = new_status
        campaign.updated_at = datetime.utcnow()
        await self.session.flush()
        return campaign
    
    async def update_progress(
        self,
        campaign_id: int,
        progress_percentage: float
    ) -> Optional[Campaign]:
        """Actualiza el porcentaje de progreso."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.update_progress(progress_percentage)
            await self.session.flush()
        return campaign
    
    async def add_spent_budget(
        self,
        campaign_id: int,
        amount: float
    ) -> Optional[Campaign]:
        """
        Añade gasto al presupuesto utilizado.
        
        Raises:
            ValueError: Si el gasto excede el presupuesto
        """
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.add_spent_budget(amount)  # Puede lanzar ValueError
            await self.session.flush()
        return campaign
    
    # ============================================
    # MÉTODOS DE NEGOCIO (usando métodos del modelo)
    # ============================================
    
    async def start_campaign(self, campaign_id: int) -> Optional[Campaign]:
        """Inicia una campaña (PLANNING -> ACTIVE)."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.start()
            await self.session.flush()
        return campaign
    
    async def complete_campaign(self, campaign_id: int) -> Optional[Campaign]:
        """Completa una campaña (ACTIVE -> COMPLETED)."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.complete()
            await self.session.flush()
        return campaign
    
    async def pause_campaign(self, campaign_id: int) -> Optional[Campaign]:
        """Pausa una campaña (ACTIVE -> PAUSED)."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.pause()
            await self.session.flush()
        return campaign
    
    async def resume_campaign(self, campaign_id: int) -> Optional[Campaign]:
        """Reanuda una campaña (PAUSED -> ACTIVE)."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.resume()
            await self.session.flush()
        return campaign
    
    async def cancel_campaign(
        self,
        campaign_id: int,
        reason: Optional[str] = None,
        cancelled_by: Optional[int] = None
    ) -> Optional[Campaign]:
        """Cancela una campaña."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.cancel(reason=reason, cancelled_by=cancelled_by)
            await self.session.flush()
        return campaign
    
    async def approve_campaign(
        self,
        campaign_id: int,
        approved_by: int
    ) -> Optional[Campaign]:
        """Aprueba una campaña."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.approve(approved_by=approved_by)
            await self.session.flush()
        return campaign
    
    # ============================================
    # OPERACIONES DELETE
    # ============================================
    
    async def delete_campaign(self, campaign_id: int) -> bool:
        """
        Elimina una campaña de forma permanente.
        
        Returns:
            True si se eliminó, False si no existía
        """
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            await self.session.delete(campaign)
            await self.session.flush()
            return True
        return False
    
    # ============================================
    # MÉTODOS DE ESTADÍSTICAS Y REPORTES
    # ============================================
    
    async def get_campaign_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de campañas.
        
        Returns:
            Dict con: total, by_status, avg_budget, total_spent, etc.
        """
        stmt = select(
            func.count(Campaign.id).label("total"),
            func.avg(Campaign.camp_budget).label("avg_budget"),
            func.sum(Campaign.camp_spent_budget).label("total_spent"),
            func.avg(Campaign.camp_progress_percentage).label("avg_progress"),
            func.avg(Campaign.camp_quality_score).label("avg_quality")
        )
        
        if user_id:
            stmt = stmt.where(Campaign.user_id == user_id)
        
        result = await self.session.execute(stmt)
        row = result.one()
        
        status_counts = await self.count_by_status(user_id)
        
        return {
            "total_campaigns": row.total or 0,
            "average_budget": float(row.avg_budget or 0),
            "total_spent": float(row.total_spent or 0),
            "average_progress": float(row.avg_progress or 0),
            "average_quality": float(row.avg_quality or 0),
            "by_status": status_counts
        }
    
    async def get_campaigns_over_budget(self, user_id: Optional[int] = None) -> List[Campaign]:
        """Obtiene campañas que han excedido su presupuesto."""
        stmt = select(Campaign).where(Campaign.camp_spent_budget > Campaign.camp_budget)
        
        if user_id:
            stmt = stmt.where(Campaign.user_id == user_id)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_campaigns_near_deadline(
        self,
        days_threshold: int = 7,
        user_id: Optional[int] = None
    ) -> List[Campaign]:
        """
        Obtiene campañas activas cercanas a su fecha de fin.
        
        Args:
            days_threshold: Días de anticipación para alertar
            user_id: Filtro opcional por usuario
        """
        from datetime import timezone, timedelta
        now = datetime.now(timezone.utc)
        threshold_date = now + timedelta(days=days_threshold)
        
        stmt = select(Campaign).where(
            and_(
                Campaign.camp_status == CampaignStatus.ACTIVE,
                Campaign.camp_end_date.isnot(None),
                Campaign.camp_end_date <= threshold_date,
                Campaign.camp_end_date >= now
            )
        )
        
        if user_id:
            stmt = stmt.where(Campaign.user_id == user_id)
        
        stmt = stmt.order_by(Campaign.camp_end_date.asc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    # ============================================
    # MÉTODOS DE TAGS
    # ============================================
    
    async def add_tag(self, campaign_id: int, tag: str) -> Optional[Campaign]:
        """Añade un tag a una campaña."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.add_tag(tag)
            await self.session.flush()
        return campaign
    
    async def remove_tag(self, campaign_id: int, tag: str) -> Optional[Campaign]:
        """Elimina un tag de una campaña."""
        campaign = await self.get_by_id(campaign_id, load_relations=False)
        if campaign:
            campaign.remove_tag(tag)
            await self.session.flush()
        return campaign
    
    async def get_all_tags(self, user_id: Optional[int] = None) -> List[str]:
        """
        Obtiene todos los tags únicos usados en campañas.
        
        Returns:
            Lista de strings (tags únicos)
        """
        # PostgreSQL specific: jsonb_array_elements_text
        from sqlalchemy import text
        
        query = """
        SELECT DISTINCT tag
        FROM campaigns, jsonb_array_elements_text(camp_tags) AS tag
        """
        
        if user_id:
            query += f" WHERE user_id = :user_id"
            result = await self.session.execute(text(query), {"user_id": user_id})
        else:
            result = await self.session.execute(text(query))
        
        return [row[0] for row in result.all()]
