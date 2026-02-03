"""
AgencIA - Dependencias DB
=========================
Inyección de sesiones para FastAPI y agentes.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.postgres.database import SessionLocal

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Generador de sesiones asíncronas para inyección de depencias."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
