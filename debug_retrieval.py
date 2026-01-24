import asyncio
import app.infrastructure.qdrant.client as qdrant_infra
from app.core.config import settings
from app.rag.embeddings import get_embedding_service
from app.rag.sparse_embedder import get_sparse_embedder
from qdrant_client.models import Prefetch

async def debug_retrieval():
    print("🔍 Diagnóstico de Recuperación...")
    
    # 1. Setup
    await qdrant_infra.connect()
    client = qdrant_infra.client_qdrant
    collection_name = settings.QDRANT_COLLECTION_NAME
    
    emb_service = get_embedding_service()
    sparse_service = get_sparse_embedder()
    
    query_text = "campaña de marketing para redes sociales"
    print(f"\n📝 Query: '{query_text}'")
    
    try:
        # 2. Generar Vectores
        print("\n⚙️ Generando Embeddings...")
        dense_vector = await emb_service.embed_text_dense(query_text)
        print(f"✅ Dense Vector generado. Dim: {len(dense_vector)}")
        print(f"   (Primeros 5 valores: {dense_vector[:5]})")
        
        sparse_vector = await sparse_service.generate_sparse_embedding(query_text)
        print(f"✅ Sparse Vector generado.")
        print(f"   Índices: {sparse_vector.indices}")
        print(f"   Valores: {sparse_vector.values}")
        
        if not sparse_vector.indices:
            print("⚠️ ADVERTENCIA: Vector disperso vacío. La búsqueda por keywords fallará.")

        # 3. Prueba Búsqueda Solo DENSA
        print("\n🔎 Prueba 1: Búsqueda SOLO DENSA (Semantic)")
        results_dense = await client.search(
            collection_name=collection_name,
            query_vector=dense_vector,
            with_vectors=True,
            with_payload=True,
            limit=3,
            using="semantic",
            score_threshold=0.1
        )
        print(f"   Resultados: {len(results_dense)}")
        for hit in results_dense:
            print(f"   - [{hit.score:.4f}] {hit.payload.get('category')} - {hit.id}")

        # 4. Prueba Búsqueda Solo DISPERSA
        print("\n🔎 Prueba 2: Búsqueda SOLO DISPERSA (Keywords)")
        results_sparse = await client.search(
            collection_name=collection_name,
            query_vector=sparse_vector,
            with_payload=True,
            limit=3,
            using="keywords",
            score_threshold=0.0
        )
        print(f"   Resultados: {len(results_sparse)}")
        for hit in results_sparse:
            print(f"   - [{hit.score:.4f}] {hit.payload.get('category')} - {hit.id}")

        # 5. Prueba Búsqueda Híbrida (Actual Implementación)
        print("\n🔎 Prueba 3: Búsqueda HÍBRIDA (Prefetch Sparse -> Query Dense)")
        prefetch_sparse = Prefetch(
            query=sparse_vector,
            using="keywords",
            limit=10
        )
        results_hybrid = await client.query_points(
            collection_name=collection_name,
            prefetch=[prefetch_sparse],
            query=dense_vector,
            using="semantic",
            limit=3,
            score_threshold=0.1,
            with_payload=True
        )
        print(f"   Resultados: {len(results_hybrid.points)}")
        for hit in results_hybrid.points:
            print(f"   - [{hit.score:.4f}] {hit.payload.get('category')} - {hit.id}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()
        await emb_service.close()

if __name__ == "__main__":
    asyncio.run(debug_retrieval())
