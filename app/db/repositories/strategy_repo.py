"""
AgencIA - Strategy Repository
=============================
Acceso a datos para Estrategias generadas.
"""

from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.strategy import Strategy
from app.db.repositories.base import BaseRepository
from app.schemas.strategy import StrategyCreate

class StrategyRepository(BaseRepository):
    """Gestión de versiones de estrategias con robustez."""
    
    async def save_strategy_version(self, strategy_in: StrategyCreate) -> Strategy:
        """Guarda una nueva versión de la estrategia."""
        async def _save():
            # Obtener última versión
            stmt = select(func.max(Strategy.stra_version)).where(Strategy.campaign_id == strategy_in.campaign_id)
            result = await self.session.execute(stmt)
            last_ver = result.scalar_one_or_none() or 0
            
            new_strategy = Strategy(
                **strategy_in.model_dump(),
                stra_version=last_ver + 1,
                stra_is_active=False 
            )
            
            self.session.add(new_strategy)
            await self.session.flush()
            return new_strategy

        return await self.execute_with_retry(_save)

    async def get_latest_strategy_by_campaign(self, campaign_id: int) -> Optional[Strategy]:
        stmt = select(Strategy).where(Strategy.campaign_id == campaign_id).order_by(Strategy.stra_version.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
