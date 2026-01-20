import os
import re
import json
import numpy as np
from collections import Counter
from typing import Dict, List, Union, Optional, Tuple
from qdrant_client.http.models import SparseVector

class SparseEmbedder:
    """
    Generador de embeddings dispersos (estilo BM25) especializado en marketing digital y economía.
    Diseñado para búsquedas híbridas en Qdrant con vocabulario persistente y stopwords bilingües.
    """
    
    def __init__(
        self,
        vocab_path: Optional[str] = None,
        stopwords_es: Optional[List[str]] = None,
        stopwords_en: Optional[List[str]] = None,
        k1: float = 1.2,
        b: float = 0.75,
        avgdl: float = 20.0
    ):
        """
        Inicializa el embedder con vocabulario persistente y parámetros BM25.
        
        Args:
            vocab_path: Ruta al archivo marketing_vocab.json. Si es None, usa vocabulario embebido.
            stopwords_es: Lista personalizada de stopwords en español. Si es None, usa lista por defecto.
            stopwords_en: Lista personalizada de stopwords en inglés. Si es None, usa lista por defecto.
            k1, b: Parámetros BM25
            avgdl: Longitud promedio de documentos en tu corpus
        """
        # Cargar vocabulario
        self.vocab = self._load_vocab(vocab_path)
        self.word_to_idx = {word: idx for idx, word in enumerate(sorted(self.vocab["vocab"]))}
        
        # Cargar stopwords bilingües
        self.stopwords = set()
        self._load_stopwords(stopwords_es, stopwords_en)
        
        # Parámetros BM25
        self.k1 = k1
        self.b = b
        self.avgdl = avgdl
        
    def _load_vocab(self, vocab_path: Optional[str]) -> Dict:
        """Carga vocabulario desde archivo en la ruta por defecto o envíada en el request"""
        if not vocab_path:
            vocab_path = os.path.join(os.path.dirname(__file__),
            '..',
            'infrastructure',
            'qdrant',
            "marketing_vocab.json"
            )
        
        with open(vocab_path, 'r', encoding='utf-8') as f:
            return json.load(f)
       
    
    def _load_stopwords(
        self,
        custom_es: Optional[List[str]] = None,
        custom_en: Optional[List[str]] = None
    ):
        """Carga stopwords en español e inglés"""
        # Stopwords en español (básicas + marketing)
        default_es = {
            "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero", "porque",
            "con", "sin", "para", "en", "sobre", "entre", "durante", "antes", "después", "desde",
            "hacia", "hasta", "bajo", "sobre", "tras", "mi", "tu", "su", "nuestro", "vuestro",
            "mío", "tuyo", "suyo", "nuestro", "vuestro", "este", "ese", "aquel", "estos", "esos",
            "aquellos", "esta", "esa", "aquella", "esto", "eso", "aquello", "quien", "cual", "donde",
            "como", "cuando", "porque", "ser", "estar", "tener", "haber", "hacer", "decir", "poder",
            "deber", "querer", "ir", "venir", "ver", "saber", "conocer", "muy", "mucho", "poco",
            "alguno", "ninguno", "todo", "otro", "mismo", "tal", "cada", "cierto", "varios",
            # Términos comunes en marketing que no son keywords
            "campana", "campaña", "auditorio", "audiencia", "mensaje", "mensaje", "palabra",
            "clave", "palabra_clave", "busqueda", "busqueda", "google", "meta", "facebook",
            "instagram", "cliente", "clientes", "negocio", "empresa", "producto", "servicio",
            "compra", "venta", "dinero", "precio", "costo", "gasto", "ingreso", "beneficio"
        }
        
        # Stopwords en inglés (básicas + marketing)
        default_en = {
            "the", "and", "or", "but", "because", "with", "without", "for", "in", "on", "at",
            "to", "from", "by", "about", "between", "during", "before", "after", "since",
            "until", "under", "over", "through", "my", "your", "his", "her", "its", "our", "their",
            "mine", "yours", "his", "hers", "ours", "theirs", "this", "that", "these", "those",
            "who", "which", "where", "when", "why", "how", "be", "is", "are", "was", "were",
            "have", "has", "had", "do", "does", "did", "will", "would", "can", "could", "should",
            "may", "might", "must", "very", "much", "many", "some", "any", "no", "all", "each",
            "every", "other", "another", "such", "what", "which", "whose", "while", "as",
            # Términos comunes en marketing que no son keywords
            "campaign", "audience", "message", "keyword", "search", "google", "meta", "facebook",
            "instagram", "client", "customer", "business", "company", "product", "service",
            "purchase", "sale", "money", "price", "cost", "spend", "revenue", "profit"
        }
        
        # Usar custom o defaults
        es_set = set(custom_es) if custom_es else default_es
        en_set = set(custom_en) if custom_en else default_en
        
        self.stopwords = es_set | en_set
        
    
    def preprocess_text(self, text: str) -> List[str]:
        """
        Preprocesa texto: normaliza, tokeniza y elimina stopwords.
        
        Args:
            text: Texto de entrada (puede contener español e inglés)
        
        Returns:
            Lista de tokens relevantes
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Normalizar: minúsculas y eliminar caracteres especiales
        text = text.lower()
        text = re.sub(r'[^\w\sáéíóúüñ]', ' ', text)  # Conserva caracteres españoles
        
        # Tokenizar
        tokens = re.findall(r'\b[\wáéíóúüñ]{2,}\b', text)  # Mínimo 2 caracteres, incluye acentos
        
        # Eliminar stopwords y tokens numéricos
        tokens = [
            token for token in tokens
            if token not in self.stopwords
            and not token.isdigit()
            and token not in {"http", "https", "www", "com", "org", "net"}
        ]
        
        return tokens
    
    def calculate_bm25_score(
        self,
        term_freq: int,
        doc_len: int,
        term: str
    ) -> float:
        """
        Calcula puntuación BM25 para un término en un documento.
        
        Args:
            term_freq: Frecuencia del término en el documento
            doc_len: Longitud del documento (número de tokens)
            term: Término a evaluar (para recuperar IDF)
        
        Returns:
            Puntuación BM25
        """
        # Componente TF de BM25
        tf_component = (term_freq * (self.k1 + 1)) / (
            term_freq + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
        )
        
        # Componente IDF (usa valor precalculado o default)
        idf_value = self.vocab.get("idf", {}).get(term, 1.5)  # Default IDF=1.5 si no existe
        
        return tf_component * idf_value
    
    
    async def generate_sparse_embedding(self, text: str) -> SparseVector:
        """
        Genera embedding disperso estilo BM25 para texto de marketing.
        
        Args:
            text: Texto a procesar (ej: descripción de campaña, objetivo de negocio)
        
        Returns:
            SparseVector listo para Qdrant
        """
        # Preprocesamiento
        tokens = self.preprocess_text(text)
        doc_len = len(tokens) if tokens else 1
        
        # Contar frecuencias
        term_freq = Counter(tokens)
        
        # Preparar vectores
        indices = []
        values = []
        
        # Procesar cada término relevante
        for term, freq in term_freq.items():
            if term in self.word_to_idx:
                idx = self.word_to_idx[term]
                score = self.calculate_bm25_score(freq, doc_len, term)
                
                if score > 0.1:  # Umbral mínimo para evitar ruido
                    indices.append(idx)
                    values.append(float(score))
        
        return SparseVector(indices=indices, values=values)
    
    def generate_batch_sparse_embeddings(self, texts: List[str]) -> List[SparseVector]:
        """Genera embeddings para múltiples textos (batch processing)"""
        return [  self.generate_sparse_embedding(text) for text in texts]

# Instancia singleton del servicio
_sparse_embedder: Optional[SparseEmbedder] = None

def get_sparse_embedder(
    vocab_path: Optional[str] = None,
    stopwords_es: Optional[List[str]] = None,
    stopwords_en: Optional[List[str]] = None
) -> SparseEmbedder:
    """
    Obtiene la instancia singleton del servicio de sparse embedder.
    
    Args:
        vocab_path: Ruta opcional al archivo de vocabulario JSON
        stopwords_es: Lista personalizada de stopwords en español (None = usar default)
        stopwords_en: Lista personalizada de stopwords en inglés (None = usar default)
    
    Returns:
        SparseEmbedder: Instancia del servicio
    """
    global _sparse_embedder
    if _sparse_embedder is None:
        _sparse_embedder = SparseEmbedder(
            vocab_path=vocab_path,
            stopwords_es=stopwords_es,
            stopwords_en=stopwords_en
        )
    return _sparse_embedder