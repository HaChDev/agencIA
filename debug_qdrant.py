import asyncio
import app.infrastructure.qdrant.client as qdrant_infra
from app.core.config import settings

async def debug_qdrant():
    print("🔍 Inspeccionando Qdrant...")
    await qdrant_infra.connect()
    
    collection_name = settings.QDRANT_COLLECTION_NAME
    print(f"Colección objetivo: {collection_name}")
    
    try:
        # 1. Obtener Info de la colección
        info = await qdrant_infra.client_qdrant.get_collection(collection_name)
        print("Estadísticas:")
        print(f" - Puntos: {info.points_count}")
        print(f" - Estado: {info.status}")
        
        if info.points_count == 0:
            print("LA COLECCIÓN ESTÁ VACÍA.")
            return

        # 2. Leer un punto para ver estructura
        print("Inspeccionando un punto de muestra...")
        points = await qdrant_infra.client_qdrant.scroll(
            collection_name=collection_name,
            limit=1,
            with_vectors=True,
            with_payload=True
        )
        
        if points[0]:
            p = points[0][0]
            print(f"ID: {p.id}")
            print(f"Payload Keys: {list(p.payload.keys())}")
            
            # Verificar nombres de vectores
            if p.vector:
                if isinstance(p.vector, dict):
                    print(f"Vectores disponibles: {list(p.vector.keys())}")
                    if "semantic" in p.vector:
                        print(f" - Dimensión 'semantic': {len(p.vector['semantic'])}")
                    if "keywords" in p.vector:
                        print(f" - Vector 'keywords' presente: Sí")
                else:
                    print(f"El vector no es un diccionario (es un solo vector sin nombre): Dim {len(p.vector)}")
            else:
                print("No hay vectores en el punto.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await qdrant_infra.client_qdrant.close()

if __name__ == "__main__":
    asyncio.run(debug_qdrant())
