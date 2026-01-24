from qdrant_client import AsyncQdrantClient, models
from app.core.config import settings

client_qdrant = None

async def connect():
    global client_qdrant

    client_qdrant = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
    )

async def disconnect():
    if client_qdrant:
        await client_qdrant.close()
