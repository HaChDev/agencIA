"""
AgencIA - Herramientas del Director (Nivel Experto)
===================================================
Herramientas que conectan el razonamiento del agente con el
Sistema RAG existente y fuentes externas simuladas.
"""

import json
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Integración con el RAG existente
import httpx
from app.core.config import settings
from app.rag import get_hybrid_retriever, RetrievalResult

# ============================================
# Schemas de Input (Estrictos)
# ============================================

class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., description="Pregunta específica sobre marketing, frameworks o datos históricos.")
    
class MarketResearchInput(BaseModel):
    industry: str = Field(..., description="Sector industrial a analizar (ej: 'Moda', 'Saas B2B').")
    region: str = Field(..., description="Región geográfica (ej: 'Colombia', 'Latam').")
    focus_areas: List[str] = Field(..., description="Áreas de foco: ['competitors', 'trends', 'customer_behavior'].")

# ============================================
# Herramientas Implementadas
# ============================================

@tool("search_knowledge_base", args_schema=SearchKnowledgeBaseInput)
async def search_knowledge_base(query: str) -> str:
    """
    Busca en la Base de Conocimiento interna de la agencia.
    Útil para recuperar:
    - Frameworks teóricos (RACE, SWOT).
    - Casos de estudio previos.
    - Benchmarks y reportes de industria.
    
    Esta herramienta usa un buscador híbrido avanzado (Semántico + Keywords).
    """
    try:
        retriever = await get_hybrid_retriever()
        # Usamos decomposition=True para que el RAG desglosé preguntas complejas
        results = await retriever.retrieve(query, use_decomposition=True)
        
        if not results:
            return "No se encontró información relevante en la base de conocimiento interna."
            
        # Formatear respuesta para el LLM (máximo 3 resultados, truncados)
        formatted_response = "### Resultados de la Base de Conocimiento:\n\n"
        for i, res in enumerate(results[:3], 1):
            formatted_response += f"**Documento {i}** (Score: {res.score:.2f})\n"
            formatted_response += f"Fuente: {res.source}\n"
            formatted_response += f"Contenido: {res.content[:500]}...\n\n"
            
        return formatted_response
    except Exception as e:
        return f"Error consultando el RAG: {str(e)}"

@tool("market_intelligence", args_schema=MarketResearchInput)
async def market_research(industry: str, region: str, focus_areas: List[str]) -> str:
    """
    Realiza una investigación de mercado profunda usando datos internos (RAG) y búsqueda web en tiempo real (Tavily).
    Combina conocimiento histórico de la agencia con tendencias actuales de internet.
    """
    # 1. Primero consultamos el RAG para ver si tenemos datos internos
    retriever = await get_hybrid_retriever()
    rag_query = f"Mercado {industry} en {region} tendencias competidores"
    rag_results = await retriever.retrieve(rag_query, use_decomposition=False)
    
    rag_summary = ""
    if rag_results:
        rag_summary = "Datos Internos:\n" + "\n".join([f"- {r.content[:200]}" for r in rag_results[:2]])
    
    # 2. Búsqueda Web Real (Tavily)
    web_data = ""
    # En producción usamos Tavily si está configurado, si no, degradamos el servicio con aviso.
    if settings.TAVILY_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": f"Market research {industry} {region} trends competitors",
                        "search_depth": "advanced",
                        "include_answer": True,
                        "max_results": 5
                    },
                    timeout=20.0
                )
                response.raise_for_status()
                data = response.json()
                
                web_data = f"**Resumen Web (Tavily AI):**\n{data.get('answer', '')}\n\n**Fuentes Externas:**\n"
                for result in data.get("results", []):
                    web_data += f"- [{result['title']}]({result['url']}): {result['content'][:250]}...\n"
                    
        except Exception as e:
            web_data = f"Error conectando a Tavily (Búsqueda Web): {str(e)}"
    else:
        web_data = "Nota: Búsqueda web externa no disponible (Sin TAVILY_API_KEY). Reporte basado estrictamente en conocimiento interno."

    report = f"""
    ### Reporte de Investigación de Mercado: {industry} ({region})

    **Enfoque**: {', '.join(focus_areas)}

    1. **Contexto Interno AgencIA**:
    {rag_summary}

    2. **Inteligencia de Mercado (Web en Tiempo Real)**:
    {web_data}
    
    **Conclusión del Analista**: Integrar hallazgos internos con tendencias externas para definir estrategia.
        """
    return report

@tool("get_channel_benchmarks")
async def get_channel_benchmarks(channel: str, metric: str) -> str:
    """
    Obtiene benchmarks de rendimiento para un canal y métrica específicos.
    Usa base de conocimiento interna de métricas históricas.
    Ej: channel='Facebook Ads', metric='CTR'
    """
    # Base de conocimiento estática de benchmarks (Puede migrarse a DB en futuro)
    benchmarks = {
        "facebook": {"ctr": "0.90% - 1.33%", "cpc": "$0.50 - $2.00"},
        "instagram": {"ctr": "0.20% - 1.00%", "cpc": "$0.40 - $1.50"},
        "linkedin": {"ctr": "0.39% - 0.60%", "cpc": "$5.00 - $8.00"},
        "google_search": {"ctr": "3.17% - 6.00%", "cpc": "$1.00 - $4.00"},
        "tiktok": {"ctr": "0.60% - 1.50%", "cpm": "$10.00"}
    }
    
    channel_key = channel.lower().split()[0] # simple match
    data = benchmarks.get(channel_key, "No data available for this channel")
    
    return f"Internal Benchmarks for {channel}:\n{json.dumps(data, indent=2)}"


def get_director_tools():
    """Retorna la lista de herramientas activas."""
    return [search_knowledge_base, market_research, get_channel_benchmarks]
