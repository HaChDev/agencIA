import redis.asyncio as redis
from app.core.config import settings

redis_client = None
redis_vector_client = None

async def connect():
    global redis_client, redis_vector_client
    
    # Conexión a Redis principal (Cache)
    redis_client = redis.from_url(
        settings.redis_url,
        decode_responses=True
    )
    
    # Conexión a Redis Vector
    redis_vector_client = redis.from_url(
        settings.redis_vector_url,
        decode_responses=True
    )

async def disconnect():
    if redis_client:
        await redis_client.close()
    if redis_vector_client:
        await redis_vector_client.close()
