from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = None
SessionLocal = None

async def connect():
    global engine, SessionLocal

    engine = create_async_engine(
        settings.postgres_url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True
    )

    SessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

async def disconnect():
    if engine:
        await engine.dispose()
