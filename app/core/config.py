"""
AgencIA - Configuración Central
================================
Gestión de variables de entorno y configuración de servicios.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    """Configuración centralizada de la aplicación."""
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ============================================
    # Aplicación
    # ============================================
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    
    # ============================================
    # API Keys
    # ============================================
    GROQ_API_KEY: str = Field(default="", description="API Key de Groq para LLM")
    OPENAI_API_KEY: str = Field(default="", description="API Key de OpenAI para embeddings")
    
    # ============================================
    # PostgreSQL
    # ============================================
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "agencia"
    POSTGRES_PASSWORD: str = "agencia_secret"
    POSTGRES_DB: str = "agencia_db"
    
    @computed_field
    @property
    def postgres_url(self) -> str:
        """URL de conexión a PostgreSQL (async)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @computed_field
    @property
    def postgres_sync_url(self) -> str:
        """URL de conexión a PostgreSQL (sync - para Alembic)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ============================================
    # Redis (Cache / Short-Memory)
    # ============================================
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "redis_secret"
    REDIS_DB: int = 0
    
    @computed_field
    @property
    def redis_url(self) -> str:
        """URL de conexión a Redis."""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ============================================
    # Redis Vector (Vector Store Auxiliar)
    # ============================================
    REDIS_VECTOR_HOST: str = "redis_vector"
    REDIS_VECTOR_PORT: int = 6380
    REDIS_VECTOR_DB: int = 0

    @computed_field
    @property
    def redis_vector_url(self) -> str:
        """URL de conexión a Redis Vector."""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_VECTOR_HOST}:{self.REDIS_VECTOR_PORT}/{self.REDIS_VECTOR_DB}"
    
    # ============================================
    # RabbitMQ
    # ============================================
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "agencia"
    RABBITMQ_PASSWORD: str = "rabbitmq_secret"
    RABBITMQ_VHOST: str = "agencia"
    
    @computed_field
    @property
    def rabbitmq_url(self) -> str:
        """URL de conexión a RabbitMQ."""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
        )
    
    # ============================================
    # Qdrant (Vector Store Principal)
    # ============================================
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = Field(default="", description="API Key opcional para Qdrant")
    # QDRANT_COLLECTION_NAME: str = "agencia_knowledge_base"
    
    @computed_field
    @property
    def qdrant_url(self) -> str:
        """URL de conexión a Qdrant."""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # ============================================
    # Embeddings
    # ============================================
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSION: int = 3072
    
    # ============================================
    # LLM (Groq)
    # ============================================
    LLM_MODEL_PRIMARY: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE_PRI: float = 0.2
    LLM_MODEL_SECONDARY: str = "openai/gpt-oss-20b"
    LLM_TEMPERATURE_SEC: float = 0.5
    
    # ============================================
    # RAG Configuration
    # ============================================
    # rag_chunk_size: int = 1000
    # rag_chunk_overlap: int = 200
    # rag_top_k: int = 5
    # rag_score_threshold: float = 0.7


@lru_cache
def get_settings() -> Settings:
    """
    Obtiene la instancia de configuración (singleton cacheado).
    
    Returns:
        Settings: Instancia de configuración
    """
    return Settings()


# Instancia global de configuración
settings = get_settings()
