"""
AgencIA - Base de Conocimiento
===============================
Gestión de documentos, chunking semántico y almacenamiento en Qdrant.
"""

import hashlib
import re
import nltk
import numpy as np
from qdrant_client import AsyncQdrantClient
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.sparse_embedder import SparseEmbedder , get_sparse_embedder
import app.infrastructure.qdrant.client as qdrant_infra
from datetime import datetime
from collections import Counter
from enum import Enum
from typing import Any, Optional
from uuid import uuid4
from dataclasses import dataclass, field
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    SparseVectorParams,
    SparseIndexParams,
    SparseVector,
    MatchValue,
    Filter,
    FieldCondition,
)


class SemanticChunker:
    """
    Implementa chunking semántico con umbral dinámico
    """
    
    def __init__(
        self,
        model_sentence_transformer: Optional[SentenceTransformer] = None,
    ):
        """
        Inicializa el chunker.
        
        Args:
            model_sentence_transformer: Modelo SentenceTransformer a usar
        """
        self.model_sentence_transformer = model_sentence_transformer or SentenceTransformer(settings.LLM_SENTENCES_TRANSFORMER)

    
    def preprocess_long_sentences(self, sentences, max_tokens=200):
        """
        Divide oraciones que exceden el límite de tokens del modelo
        """
        processed_sentences = []
        for sentence in sentences:
            # Estimación rápida de tokens (1 token ≈ 4 caracteres)
            estimated_tokens = len(sentence) // 4
            
            if estimated_tokens > max_tokens:
                # Dividir en fragmentos más pequeños
                words = sentence.split()
                chunks = []
                current_chunk = []
                current_length = 0
            
                for word in words:
                    current_chunk.append(word)
                    current_length += len(word) + 1  # +1 para el espacio
                    
                    if current_length // 4 > max_tokens:  # Estimación de tokens
                        chunks.append(" ".join(current_chunk))
                        current_chunk = []
                        current_length = 0
                
                if current_chunk:
                    chunks.append(" ".join(current_chunk))  
                
                processed_sentences.extend(chunks)  
            else:
                processed_sentences.append(sentence)
        
        return processed_sentences

    

    def semantic_chunking(self, texto_string: str):
        """
        Crea chunks semánticos del texto string
        """
        # Divide el texto en sentencias
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
            
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            nltk.download('punkt_tab', quiet=True)
        sentences = nltk.sent_tokenize(texto_string)

        if len(sentences) < 2:
            return [texto_string]

        # Preprocesar oraciones muy largas
        sentences = self.preprocess_long_sentences(sentences, max_tokens=200)

        # Embeddings locales para análisis de similitud
        embeddings = self.model_sentence_transformer.encode(sentences)

        # Calcular similitudes entre oraciones consecutivas
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
            similarities.append(sim)

        # Umbral dinámico (Subir al percentil hace mas agresivo el dividir)
        threshold = np.percentile(similarities, 5)

        # Fusión en chunks
        chunks = []
        current_chunk = [sentences[0]]
        current_word_count = len(sentences[0].split())
        
        for i, sim in enumerate(similarities):
            sentence_to_add = sentences[i+1]
            sentence_word_count = len(sentence_to_add.split())
            
            # Dividir si la similitud es baja O si el chunk actual ya es muy grande (> 900 palabras)
            if sim < threshold or (current_word_count + sentence_word_count > 900):
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence_to_add]
                current_word_count = sentence_word_count
            else:
                current_chunk.append(sentence_to_add)
                current_word_count += sentence_word_count
    
        chunks.append(" ".join(current_chunk))
        
        print(f"DEBUG: Texto de {len(texto_string.split())} palabras dividido en {len(chunks)} chunks semánticos.")
        return chunks
        

    
class KnowledgeBase:
    """
    Base de conocimiento vectorial.
    
    Gestiona el almacenamiento y recuperación de documentos
    en Qdrant con embeddings generados por OpenAI.
    """
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
        sparse_embedder: Optional[SparseEmbedder] = None
    ):
        """
        Inicializa la base de conocimiento.
        
        Args:
            collection_name: Nombre de la colección en Qdrant
            embedding_service: Servicio de embeddings a usar
            sparse_embedder: Servicio de sparse embedder a usar
        """
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.embedding_service = embedding_service or get_embedding_service()
        self.sparse_embedder = sparse_embedder or get_sparse_embedder()
        self.chunker = SemanticChunker()
    
    @property
    def client(self) -> AsyncQdrantClient:
        # Usar el cliente global desde el módulo para asegurar referencia actualizada
        return qdrant_infra.client_qdrant
    
    async def initialize(self):
        """
        Inicializa la colección en Qdrant si no existe.
        """

        collections = await self.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if self.collection_name not in collection_names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    # Vector denso (embeddings semánticos de OpenAI)
                    "semantic": VectorParams(
                        size=settings.EMBEDDING_DIMENSION,   # text-embedding-3-small produce 1536 dimensiones
                        distance=Distance.COSINE
                    ),
                },
                sparse_vectors_config={
                    # Vector disperso (BM25 para keywords)
                    "keywords": SparseVectorParams(
                        index=SparseIndexParams(
                            on_disk=False
                        )
                    ),
                }
            )
            print(f"Colección '{self.collection_name}' creada en Qdrant")

    
    async def extract_text(self, url_archivo: str) -> str:
        """
        Extrae el texto crudo de un archivo y normaliza espacios en blanco.
        """
        with open(url_archivo, "r", encoding="utf-8") as f:
            texto_crudo = f.read()
        
        import re
        # 1. Normalizar saltos de línea: reemplazar 3 o más saltos por solo 2 (evita huecos gigantes)
        texto_limpio = re.sub(r'\n{3,}', '\n\n', texto_crudo)
        
        # 2. Limpiar espacios en blanco al final de cada línea pero mantener estructura
        texto_limpio = "\n".join([line.strip() for line in texto_limpio.splitlines()])
        
        return texto_limpio.strip()
    

    async def add_document(self, url_archivo: str,
    category,
    source_author,
    year,
    is_evergreen,
    topic_tags,
    industry_sector,
    original_document ) -> int:
        """
        Procesa y almacena un documento a la base de conocimiento.
        
        Args:
            texto_crudo: Texto crudo a añadir
            category: Categoría del documento
            source_author: Autor del documento
            year: Año del documento
            is_evergreen: Indica si el documento es evergreen (conocimiento base que no cambia)
            topic_tags: Tags de tema
            industry_sector: Sector industrial
            original_document: Documento original
            
        Returns:
            int: Cantidad de chunks añadidos
        """
        # Chunking semántico
        texto_string = await self.extract_text(url_archivo)
        chunks = self.chunker.semantic_chunking(texto_string)
        document_id = str(uuid4())
        
        if not chunks:
            return 0
        
        # Preparar puntos para Qdrant
        points = []

        # Generar embeddings
        for idx, chunk in enumerate(chunks):
            # Generar embeddings
            dense_vector = await self.embedding_service.embed_text_dense(chunk)
            sparse_vector = await self.sparse_embedder.generate_sparse_embedding(chunk)
            
            # Crear punto con payload estructurado  
            point = PointStruct(
                id=str(uuid4()),
                vector={
                    "semantic": dense_vector,
                    "keywords": sparse_vector
                },
                payload={
                    # Contenido
                    "content": chunk,
                    
                    # Nivel 1: Clasificación Macro
                    "category": category,  # "Framework", "Teoría", "Reporte", "Caso de Estudio"
                    "source_author": source_author,
                    
                    # Nivel 2: Contexto Temporal
                    "year": year,
                    "is_evergreen": is_evergreen,  # False para Reportes de Tendencias true para teoria
                    
                    # Nivel 3: Segmentación de Marketing
                    "topic_tags": topic_tags,
                    "industry_sector": industry_sector,
                    
                    # Nivel 4: Trazabilidad
                    "original_document": original_document,
                    "document_id": document_id,
                    "chunk_id": idx
                }
            )
        
            points.append(point)
    
        # Insertar en Qdrant
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"{len(points)} chunks ingresados exitosamente")
        return len(points)
        
    
    # async def delete_document(self, document_id: str):
    #     """
    #     Elimina todos los chunks de un documento.
        
    #     Args:
    #         document_id: ID del documento a eliminar
    #     """
    #     client = await self.client
    #     await client.delete(
    #         collection_name=self.collection_name,
    #         points_selector=Filter(
    #             must=[
    #                 FieldCondition(
    #                     key="document_id",
    #                     match=MatchValue(value=document_id)
    #                 )
    #             ]
    #         )
    #     )
    
    async def get_stats(self) -> dict:
        """
        Obtiene estadísticas de la base de conocimiento.
        
        Returns:
            Diccionario con estadísticas
        """
        collection_info = await self.client.get_collection(self.collection_name)
        
        return {
            "collection_name": self.collection_name,
            "vectors_count": getattr(collection_info, "vectors_count", 0),
            "points_count": getattr(collection_info, "points_count", 0),
            "status": getattr(collection_info.status, "value", str(collection_info.status))
        }
    

# Instancia singleton
_knowledge_base: Optional[KnowledgeBase] = None


async def get_knowledge_base() -> KnowledgeBase:

    """
    Obtiene la instancia singleton de la base de conocimiento.
    
    Returns:
        KnowledgeBase: Instancia inicializada
    """
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
        await _knowledge_base.initialize()
    return _knowledge_base
