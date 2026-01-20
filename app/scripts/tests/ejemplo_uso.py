"""
AgencIA - Ejemplo de Uso del Sistema de Testing RAG
====================================================
Script de ejemplo mostrando diferentes formas de usar el sistema de testing.
"""

import httpx
import asyncio
from pathlib import Path


# ============================================
# Configuración
# ============================================
API_BASE_URL = "http://localhost:8000"


# ============================================
# Ejemplo 1: Ingesta de Documento Individual
# ============================================
async def ejemplo_ingesta_individual():
    """
    Ejemplo de cómo ingestar un documento individual con metadatos personalizados.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 1: Ingesta de Documento Individual")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        request_data = {
            "file_path": "doc/ag_director_estrategia.txt",
            "category": "Framework",
            "source_author": "AgencIA Team",
            "year": 2024,
            "is_evergreen": True,
            "topic_tags": ["estrategia", "agentes", "director"],
            "industry_sector": "Marketing Digital"
        }
        
        print(f"\n📄 Ingresando: {request_data['file_path']}")
        print(f"📋 Categoría: {request_data['category']}")
        print(f"👤 Autor: {request_data['source_author']}")
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/test/ingest-document",
                json=request_data,
                timeout=60.0
            )
            
            if response.status_code == 201:
                result = response.json()
                print(f"\n✅ Ingesta exitosa!")
                print(f"   Chunks añadidos: {result['chunks_added']}")
                print(f"   Total en colección: {result['collection_stats']['count']}")
            else:
                print(f"\n❌ Error: {response.status_code}")
                print(f"   {response.json()}")
        
        except Exception as e:
            print(f"\n❌ Excepción: {str(e)}")


# ============================================
# Ejemplo 2: Ingesta Masiva de Carpeta
# ============================================
async def ejemplo_ingesta_masiva():
    """
    Ejemplo de cómo ingestar todos los documentos de una carpeta.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 2: Ingesta Masiva de Carpeta")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        params = {
            "directory_path": "doc/framework",
            "source_author": "AgencIA Team",
            "year": 2024,
            "is_evergreen": True,
            "industry_sector": "Marketing Digital"
        }
        
        print(f"\n📁 Escaneando: {params['directory_path']}")
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/test/ingest-directory",
                params=params,
                timeout=300.0  # 5 minutos para carpetas grandes
            )
            
            if response.status_code == 201:
                result = response.json()
                print(f"\n✅ Ingesta masiva completada!")
                print(f"   Archivos procesados: {result['total_files']}")
                print(f"   Total de chunks: {result['total_chunks']}")
                print(f"\n📊 Detalle por archivo:")
                for file_result in result['results']:
                    status_icon = "✅" if file_result['status'] == 'success' else "❌"
                    print(f"   {status_icon} {Path(file_result['file']).name}")
                    if file_result['status'] == 'success':
                        print(f"      - Chunks: {file_result['chunks_added']}")
                        print(f"      - Categoría: {file_result['category']}")
            else:
                print(f"\n❌ Error: {response.status_code}")
                print(f"   {response.json()}")
        
        except Exception as e:
            print(f"\n❌ Excepción: {str(e)}")


# ============================================
# Ejemplo 3: Estadísticas de la Colección
# ============================================
async def ejemplo_estadisticas():
    """
    Ejemplo de cómo obtener estadísticas de la colección Qdrant.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 3: Estadísticas de la Colección")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/test/collection-stats",
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                stats = result['stats']
                print(f"\n📊 Estadísticas de la colección:")
                print(f"   Total de puntos: {stats.get('count', 0)}")
                print(f"   Nombre colección: {stats.get('collection_name', 'N/A')}")
            else:
                print(f"\n❌ Error: {response.status_code}")
        
        except Exception as e:
            print(f"\n❌ Excepción: {str(e)}")


# ============================================
# Ejemplo 4: Validación de Ingesta
# ============================================
async def ejemplo_validacion():
    """
    Ejemplo de cómo validar que un documento fue ingresado correctamente.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 4: Validación de Ingesta")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        file_name = "ag_director_estrategia.txt"
        
        print(f"\n🔍 Validando: {file_name}")
        
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/test/validate-ingestion/{file_name}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n📋 Resultado de validación:")
                print(f"   Documento: {result['document']}")
                print(f"   Validación: {'✅ PASÓ' if result['validation_passed'] else '❌ FALLÓ'}")
                print(f"\n   Checks:")
                for check in result['checks']:
                    status = "✅" if check['passed'] else "❌"
                    print(f"   {status} {check['check']}: {check['message']}")
            else:
                print(f"\n❌ Error: {response.status_code}")
        
        except Exception as e:
            print(f"\n❌ Excepción: {str(e)}")


# ============================================
# Ejecutar Todos los Ejemplos
# ============================================
async def main():
    """
    Ejecuta todos los ejemplos en secuencia.
    """
    print("\n" + "=" * 60)
    print("SISTEMA DE TESTING DINÁMICO PARA RAG - AgencIA")
    print("=" * 60)
    print("\nEjecutando ejemplos de uso...")
    
    # Ejecutar ejemplos
    await ejemplo_estadisticas()
    await ejemplo_ingesta_individual()
    await ejemplo_validacion()
    # await ejemplo_ingesta_masiva()  # Comentado por defecto (puede tardar)
    
    print("\n" + "=" * 60)
    print("Ejemplos completados")
    print("=" * 60)
    print("\n💡 Tip: Accede a http://localhost:8000/docs para ver la documentación interactiva\n")


if __name__ == "__main__":
    """
    Para ejecutar este script:
    
    1. Asegúrate de que la aplicación esté corriendo:
       docker-compose up -d
       uvicorn app.main:app --reload
    
    2. Ejecuta este script:
       python app/scripts/tests/ejemplo_uso.py
    """
    asyncio.run(main())
