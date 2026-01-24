"""
AgencIA - Retriever Híbrido Avanzado
====================================
Sistema de recuperación que combina:
1. Descomposición de Queries (LLM)
2. Búsqueda Híbrida (Densa + Dispersa) en Qdrant
3. Re-ranking (Cohere)
"""

import json
import cohere
from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings
from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.sparse_embedder import SparseEmbedder, get_sparse_embedder
from app.rag.knowledge_base import KnowledgeBase, get_knowledge_base

from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

@dataclass
class RetrievalResult:
    """Resultado de una búsqueda en el retriever."""
    id: str
    content: str
    score: float
    source: str
    metadata: dict
    retrieval_method: str = "hybrid"

class SubQuery(BaseModel):
    query: str = Field(description="La consulta de búsqueda refinada")
    filters: Dict[str, Any] = Field(description="Filtros de metadatos (año, categoría, etc)", default={})

class DecomposedQueries(BaseModel):
    sub_queries: List[SubQuery] = Field(description="Lista de sub-consultas descompuestas")

class QueryDecomposer:
    """
    Descompone consultas complejas usando LLM (Groq) para generar 
    sub-consultas y filtros de metadatos precisos.
    """
    
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            model_name=settings.LLM_MODEL_SECONDARY,
            groq_api_key=settings.GROQ_API_KEY
        )
        
        self.parser = JsonOutputParser(pydantic_object=DecomposedQueries)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en recuperación de información para una agencia de marketing.
            Tu tarea es descomponer preguntas complejas de usuarios en sub-consultas precisas para una base de datos vectorial.
            
            Para cada sub-consulta, debes identificar filtros de metadatos si aplican.
            Los metadatos disponibles son:
            - category: "Framework", "Teoría", "Reporte", "Caso de Estudio"
            - year: año del documento (int)
            - industry_sector: Sector industrial (ej: "Tecnología", "F&B", "Moda")
            - topic_tags: Lista de tags
            
            Ejemplo:
            Pregunta: "Tendencias de café en Colombia 2024 y estrategias de marketing"
            Salida JSON:
            {{
                "sub_queries": [
                    {{
                        "query": "Tendencias consumo café Colombia",
                        "filters": {{ "year": 2024, "industry_sector": "F&B" }}
                    }},
                    {{
                        "query": "Estrategias marketing cafeterías",
                        "filters": {{ "category": "Caso de Estudio" }}
                    }}
                ]
            }}
            
            IMPORTANTE:
            - Sé CONSERVADOR con los filtros. Si no estás seguro, NO agregues filtros.
            - "category": Solo usa si el usuario pide explícitamente "reporte", "caso de estudio", etc.
            - "year": Solo usa si el usuario menciona un año específico.
            - "industry_sector": Solo si el usuario menciona un sector específico.
            
            Si la pregunta es general y no estas totalmente seguro de los filtros, devuelve "filters": {{}}
            
            IMPORTANTE: Responde ÚNICAMENTE con el JSON válido."""),
            ("human", "{query}")
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    async def decompose(self, query: str) -> List[SubQuery]:
        """Descompone la consulta original."""
        try:
            result = await self.chain.ainvoke({"query": query})
            # Convertir dicts a objetos SubQuery
            return [SubQuery(**sq) for sq in result.get("sub_queries", [])]
        except Exception as e:
            print(f"Error en descomposición de query: {e}")
            # Fallback: usar query original sin filtros
            return [SubQuery(query=query)]

class CohereReranker:
    """Servicio de Re-ranking usando Cohere."""
    
    def __init__(self, api_key: str):
        self.client = cohere.ClientV2(api_key)
        
    def rerank(self, query: str, documents: List[RetrievalResult], top_n: int = 5) -> List[RetrievalResult]:
        if not documents:
            return []
            
        # Preparar documentos para Cohere
        docs_text = [doc.content for doc in documents]
        
        try:
            results = self.client.rerank(
                query=query,
                documents=docs_text,
                top_n=top_n,
                model=settings.LLM_RERANKER_MODEL
            )
            
            reranked_results = []
            for hit in results.results:
                original_doc = documents[hit.index]
                # Actualizar score con el de Cohere
                original_doc.score = hit.relevance_score
                reranked_results.append(original_doc)
                
            return reranked_results
            
        except Exception as e:
            print(f"Error en Cohere Rerank: {e}")
            return documents[:top_n] # Fallback: devolver los primeros sin re-rank

class HybridRetriever:
    """
    Retriever avanzado con:
    - Query Decomposition (LLM)
    - Hybrid Search (Qdrant)
    - Re-ranking (Cohere)
    """
    
    def __init__(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        embedding_service: Optional[EmbeddingService] = None,
        sparse_embedder: Optional[SparseEmbedder] = None,
        top_k: int = 10
    ):
        self._knowledge_base = knowledge_base
        self._embedding_service = embedding_service
        self._sparse_embedder = sparse_embedder
        self.top_k = top_k
        
        self.decomposer = QueryDecomposer()
        self.reranker = CohereReranker(api_key=settings.COHERE_API_KEY) if settings.COHERE_API_KEY else None

    async def _get_knowledge_base(self) -> KnowledgeBase:
        if self._knowledge_base is None:
            self._knowledge_base = await get_knowledge_base()
        return self._knowledge_base
    
    def _get_embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    def _get_sparse_embedder(self) -> SparseEmbedder:
        if self._sparse_embedder is None:
            self._sparse_embedder = get_sparse_embedder()
        return self._sparse_embedder


    def _build_qdrant_filter(self, filters_dict: Dict[str, Any]) -> Optional[Filter]:
        """Convierte diccionario plano a Qdrant Filter."""
        if not filters_dict:
            return None
            
        conditions = []
        for key, value in filters_dict.items():
            if isinstance(value, list):
                # Si es lista, usamos MatchAny
                conditions.append(
                    FieldCondition(key=key, match=MatchAny(any=value))
                )
            else:
                # Match exacto para valores simples
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
        
        return Filter(must=conditions) if conditions else None


    async def retrieve(self, query: str, use_decomposition: bool = True) -> List[RetrievalResult]:
        """
        Ejecuta el pipeline completo de recuperación.
        """
        kb = await self._get_knowledge_base()
        emb_service = self._get_embedding_service()
        sparse_service = self._get_sparse_embedder()
        
        # 1. Descomposición de Query
        sub_queries = [SubQuery(query=query)]
        if use_decomposition:
            print(f"Descomponiendo query: {query}")
            sub_queries = await self.decomposer.decompose(query)
            print(f"Sub-queries generadas: {[sq.query for sq in sub_queries]}")

        all_results = {}
        
        # 2. Ejecutar búsquedas en paralelo o secuencial
        for sq in sub_queries:
            # Generar vectores
            dense_vector = await emb_service.embed_text_dense(sq.query)
            sparse_vector = await sparse_service.generate_sparse_embedding(sq.query)
            
            # Construir filtros
            qdrant_filter = self._build_qdrant_filter(sq.filters)
            
            # Verificar validez del vector disperso
            has_sparse = len(sparse_vector.indices) > 0
            
            if has_sparse:
                # Búsqueda Híbrida con Prefetch
                qdrant_results = await kb.search_hybrid(
                    query_dense=dense_vector,
                    query_sparse=sparse_vector,
                    filter_conditions=qdrant_filter,
                    top_k=self.top_k,
                    score_threshold=0.4
                )
            else:
                print(f"Vector disperso vacío para: '{sq.query}'. Usando solo búsqueda semántica.")
                # Búsqueda solo Semántica (sin prefetch disperso)
                qdrant_results = await kb.client.query_points(
                    collection_name=kb.collection_name,
                    query=dense_vector,
                    using="semantic",
                    limit=self.top_k,
                    query_filter=qdrant_filter,
                    score_threshold=0.4, # Mantener umbral de calidad
                    with_payload=True
                )
                qdrant_results = qdrant_results.points
            
            # -----------------------------------------------------------------
            # FALLBACK STRATEGY: Si no hay resultados con filtros, intentar sin filtros
            # -----------------------------------------------------------------
            if not qdrant_results and qdrant_filter is not None:
                print(f"Sin resultados con filtros estrictos para: '{sq.query}'. Reintentando sin filtros...")
                
                if has_sparse:
                    qdrant_results = await kb.search_hybrid(
                        query_dense=dense_vector,
                        query_sparse=sparse_vector,
                        filter_conditions=None, # Quitar filtros
                        top_k=self.top_k,
                        score_threshold=0.4
                    )
                else:
                    # Fallback solo semántico
                    qdrant_results = await kb.client.query_points(
                        collection_name=kb.collection_name,
                        query=dense_vector,
                        using="semantic",
                        limit=self.top_k,
                        query_filter=None, # Quitar filtros
                        score_threshold=0.4,
                        with_payload=True
                    )
                    qdrant_results = qdrant_results.points

            # Procesar resultados
            for hit in qdrant_results:
                # Evitar duplicados (usar ID del documento como clave)
                doc_id = hit.id
                if doc_id not in all_results:
                    all_results[doc_id] = RetrievalResult(
                        id=doc_id,
                        content=hit.payload.get("content", ""),
                        score=hit.score,
                        source=hit.payload.get("source_author", "Desconocido"),
                        metadata={k:v for k,v in hit.payload.items() if k != "content"}
                    )
                else:
                    # Si ya existe, podríamos sumar scores (fusión simple) o mantener el máximo
                    if hit.score > all_results[doc_id].score:
                        all_results[doc_id].score = hit.score
        
        unique_results = list(all_results.values())
        
        # 3. Re-ranking con Cohere
        if self.reranker and unique_results:
            print(f"Re-ranking {len(unique_results)} documentos con Cohere...")
            final_results = self.reranker.rerank(query, unique_results, top_n=self.top_k)
        else:
            # Ordenar por score original si no hay reranker
            final_results = sorted(unique_results, key=lambda x: x.score, reverse=True)[:self.top_k]
            
        return final_results

# Instancia singleton
_hybrid_retriever: Optional[HybridRetriever] = None

async def get_hybrid_retriever() -> HybridRetriever:
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever(
            top_k=settings.RAG_TOP_K
        )
    return _hybrid_retriever
