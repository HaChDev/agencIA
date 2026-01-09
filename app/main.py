"""
AgencIA - Punto de Entrada Principal
=====================================
API FastAPI para la agencia de marketing con IA.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import get_api_router
from app.infrastructure.postgres.database import connect as pg_connect, disconnect as pg_disconnect
from app.infrastructure.redis.client import connect as redis_connect, disconnect as redis_disconnect
from app.infrastructure.rabbitmq_cliente.connection import connect as rmq_connect, disconnect as rmq_disconnect
from app.infrastructure.qdrant.client import connect as qdrant_connect, disconnect as qdrant_disconnect
import debugpy
import os

if os.getenv("APP_DEBUG", "false").lower() == "true":
    debugpy.listen(("0.0.0.0", 5678))
    debugpy.wait_for_client()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    Inicializa y cierra conexiones a servicios externos.
    """
    # Startup
    print("Iniciando AgencIA ...")
    
    await pg_connect()
    await redis_connect()
    await qdrant_connect()
    await rmq_connect()

    yield
    
    # Shutdown
    print("Cerrando AgencIA...")
    await pg_disconnect()
    await redis_disconnect()
    await rmq_disconnect()
    await qdrant_disconnect()


app = FastAPI(
    title="AgencIA API",
    description="API de la primera agencia de marketing digital operada por agentes de IA",
    version="0.1.0",
    lifespan=lifespan,
)

# Configurar CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"] if settings.app_debug else [],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Incluir rutas de la API
app.include_router(get_api_router())


@app.get("/")
async def root():
    """Endpoint raíz de la API."""
    return {
        "name": "AgencIA API",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.app_env
    }


@app.get("/health")
async def health_check():
    """
    Health check para verificar el estado de la aplicación.
    
    Returns:
        dict: Estado de la aplicación y servicios
    """
    return {
        "status": "healthy",
        "services": {
            "api": "up",
            "postgres": "pending",
            "redis": "pending",
            "rabbitmq": "pending",
            "qdrant": "pending"
        }
    }
