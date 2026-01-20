"""
AgencIA - RAG Module Init
==========================
Exporta los componentes del sistema RAG.
"""

from app.rag.embeddings import (
    EmbeddingService,
    get_embedding_service
)
from app.rag.knowledge_base import (
    KnowledgeBase,
    SemanticChunker,
    get_knowledge_base
)

from app.rag.retriever import (
    HybridRetriever,
    RetrievalResult,
    QueryDecomposer,
    get_hybrid_retriever
)

__all__ = [
    # Embeddings
    "EmbeddingService",
    "get_embedding_service",
    # Knowledge Base
    "KnowledgeBase",
    "SemanticChunker",
    "get_knowledge_base",
    # Retriever
    "HybridRetriever",
    "RetrievalResult",
    "QueryDecomposer",
    "get_hybrid_retriever"
]
