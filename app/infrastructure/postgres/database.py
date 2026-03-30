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


# Dependencia de FastAPI para obtener la sesión de base de datos
async def get_db_session():
    # Asegurarse de que SessionLocal está inicializado
    if SessionLocal is None:
        raise RuntimeError("Error en base de datos sesion no inicializada. llamar primero el metodo connect().")
    
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()