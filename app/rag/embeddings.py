"""
AgencIA - Servicio de Embeddings
=================================
Generación de embeddings usando OpenAI.
"""

from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings


class EmbeddingService:
    """
    Servicio para generar embeddings de texto.

    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None
    ):
        """
        Inicializa el servicio de embeddings.
        
        Args:
            api_key: API Key de OpenAI (usa config si no se especifica)
            model: Modelo de embeddings (usa config si no se especifica)
            dimension: Dimensión de los embeddings (usa config si no se especifica)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        
        self._client: Optional[AsyncOpenAI] = None
    
    @property
    def client(self) -> AsyncOpenAI:
        """Cliente OpenAI (inicialización lazy)."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client


    async def embed_text_dense(self, text: str) -> list[float]:
        """
        Genera el embedding para un texto.
        
        Args:
            text: Texto a convertir en embedding
            
        Returns:
            list[float]: Vector de embedding con dimensión configurada
        """
        # Limpiar texto
        text = text.replace("\n", " ").strip()
        
        if not text:
            return [0.0] * self.dimension
        
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimension
        )
        return response.data[0].embedding
        

    async def close(self):
        """Cierra el cliente de OpenAI."""
        if self._client is not None:
            await self._client.close()
            self._client = None

# Instancia singleton del servicio
_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    """
    Obtiene la instancia singleton del servicio de embeddings.
    
    Returns:
        EmbeddingService: Instancia del servicio
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service