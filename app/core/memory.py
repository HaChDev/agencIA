"""
AgencIA - Gestion de Memoria y Redis
====================================
Implementación de persistencia para LangGraph usando Redis y gestión de estado compartido.
"""

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional, Sequence, Tuple

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
import redis.asyncio as redis

from app.core.config import settings

class AsyncRedisCheckpointSaver(BaseCheckpointSaver):
    """
    Implementación de CheckpointSaver con Namespacing para sistemas multiagente.
    Aísla el estado de cada agente (Director, Content, Ads, etc.) en Redis.
    """
    def __init__(self, client: redis.Redis, namespace: str = "director"):
        super().__init__(serde=JsonPlusSerializer())
        self.client = client
        self.namespace = namespace

    def _get_key_prefix(self, thread_id: str) -> str:
        """Genera el prefijo de llave aislado por agente y hilo."""
        return f"agencia:{self.namespace}:thread:{thread_id}"

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None,
    ) -> RunnableConfig:
        """
        Guarda un checkpoint en Redis con TTL para optimización de RAM.
        Optimizado con Pipeline para velocidad.
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint.get("id") or metadata.get("checkpoint_id") or "latest"
        
        prefix = self._get_key_prefix(thread_id)
        key = f"{prefix}:checkpoint:{checkpoint_id}"
        latest_key = f"{prefix}:latest"
        
        data = {
            "checkpoint": self.serde.dumps(checkpoint),
            "metadata": self.serde.dumps(metadata),
        }
        
        # Usamos un pipeline para asegurar velocidad y atomicidad
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping=data)
            pipe.expire(key, settings.REDIS_CHECKPOINT_TTL)
            
            pipe.set(latest_key, checkpoint_id)
            pipe.expire(latest_key, settings.REDIS_SESSION_TTL)
            
            await pipe.execute()
        
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Recupera el estado exacto o el último disponible del agente específico."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")
        
        prefix = self._get_key_prefix(thread_id)
        
        # Si no piden un ID específico, buscamos el puntero 'latest' de este agente
        if not checkpoint_id:
            checkpoint_id_bytes = await self.client.get(f"{prefix}:latest")
            if not checkpoint_id_bytes:
                return None
            checkpoint_id = checkpoint_id_bytes.decode("utf-8")
            
        key = f"{prefix}:checkpoint:{checkpoint_id}"
        data = await self.client.hgetall(key)
        
        if not data:
            return None
            
        checkpoint = self.serde.loads(data[b"checkpoint"])
        metadata = self.serde.loads(data[b"metadata"])
        
        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None 
        )

    # Implementaciones síncronas requeridas por la clase base (no usadas en async)
    def put(self, config, checkpoint, metadata, new_versions):
        raise NotImplementedError("Use aput for async Redis")

    def get_tuple(self, config):
        raise NotImplementedError("Use aget_tuple for async Redis")
        
    def list(self, config, *, filter = None, before = None, limit = None):
         raise NotImplementedError("List not implemented yet")


class MemoryService:
    """
    Servicio central de memoria para la agencia multiagente.
    """
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        
    async def initialize(self):
        """Inicializa la conexión a Redis."""
        if not self._redis_client:
            self._redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False # Necesario False para bytes en algunos casos, o manejarlo con cuidado
            )
            
    async def get_redis_client(self) -> redis.Redis:
        """Obtiene el cliente raw de Redis."""
        if not self._redis_client:
            await self.initialize()
        return self._redis_client # type: ignore

    async def get_checkpointer(self, namespace: str = "director") -> AsyncRedisCheckpointSaver:
        """Devuelve un checkpointer configurado y aislado para un agente específico."""
        client = await self.get_redis_client()
        return AsyncRedisCheckpointSaver(client, namespace=namespace)

    async def close(self):
        if self._redis_client:
            await self._redis_client.close()

# Singleton
_memory_service = MemoryService()

async def get_memory_service() -> MemoryService:
    return _memory_service

async def get_redis_checkpointer(namespace: str = "director") -> AsyncRedisCheckpointSaver:
    service = await get_memory_service()
    return await service.get_checkpointer(namespace=namespace)
