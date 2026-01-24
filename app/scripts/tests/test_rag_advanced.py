import asyncio
import os
from app.rag.retriever import get_hybrid_retriever

async def test_rag():
    print("Iniciando prueba de RAG Avanzado...")
    
    retriever = await get_hybrid_retriever()
    
    # Consulta compleja para probar descomposición
    query = "que debo saber para crear una campaña de marketing para redes sociales en el 2024 y 2025"
    
    print(f"Consulta: {query}")
    print("-" * 50)
    
    results = await retriever.retrieve(query, use_decomposition=True)
    
    print(f"Resultados encontrados: {len(results)}")
    for i, res in enumerate(results, 1):
        print(f"[{i}] Score: {res.score:.4f} | Source: {res.source}")
        print(f"Content: {res.content[:200]}...")
        print(f"Metadata: {res.metadata.get('topic_tags', [])}")

    return results