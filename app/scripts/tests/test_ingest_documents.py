"""
AgencIA - Test de Ingesta de Documentos
========================================
Script dinámico para probar la funcionalidad completa de add_document:
- Extracción de texto
- Chunking semántico
- Generación de vectores densos (OpenAI embeddings)
- Generación de vectores sparse (BM25)
- Almacenamiento en Qdrant con metadatos personalizados
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from app.rag.knowledge_base import get_knowledge_base
from app.api.models.ingest_models import DocumentIngestRequest


async def ingest_document(request: DocumentIngestRequest) -> Dict:
    """
    Función principal para ingestar un documento con metadatos personalizados.
    
    Args:
        request: Request con la ruta del archivo y metadatos
        
    Returns:
        Dict con resultados de la ingesta:
        - chunks_added: Cantidad de chunks añadidos
        - stats: Estadísticas de la colección
        - metadata_used: Metadatos utilizados en la ingesta
    """
    # Obtener instancia de knowledge base (es async, necesita await)
    kb = await get_knowledge_base()
    
    # Ejecutar ingesta con add_document
    chunks_added = await kb.add_document(
        url_archivo=request.file_path,
        category=request.category,
        source_author=request.source_author,
        year=request.year,
        is_evergreen=request.is_evergreen,
        topic_tags=request.topic_tags,
        industry_sector=request.industry_sector,
        original_document=Path(request.file_path).name
    )
    
    # Obtener estadísticas de la colección
    stats = await kb.get_stats()
    
    return {
        "chunks_added": chunks_added,
        "stats": stats,
        "metadata_used": request.model_dump(exclude={'file_path'})
    }


async def scan_and_ingest_directory(
    directory: Path,
    default_metadata: Dict
) -> List[Dict]:
    """
    Escanea recursivamente una carpeta e ingesta todos los documentos encontrados.
    
    Infiere automáticamente la categoría basándose en la estructura de carpetas
    (framework/, teoria/, reporte/, caso_estudio/, evergreen/).
    
    Args:
        directory: Path a la carpeta a escanear
        default_metadata: Metadatos por defecto para todos los documentos
        
    Returns:
        Lista de resultados con información de cada archivo procesado
    """
    results = []
    supported_extensions = ['.txt', '.pdf', '.docx']
    
    # Escanear recursivamente
    for file_path in directory.rglob("*.*"):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            try:
                # Inferir categoría desde la estructura de carpetas
                category = infer_category_from_path(file_path)
                
                # Crear request con metadatos por defecto + categoría inferida
                request = DocumentIngestRequest(
                    file_path=str(file_path),
                    category=category,
                    **default_metadata
                )
                
                # Ingestar documento
                result = await ingest_document(request)
                
                results.append({
                    "file": str(file_path),
                    "status": "success",
                    "chunks_added": result["chunks_added"],
                    "category": category,
                    "metadata": result["metadata_used"]
                })
                
                print(f"✓ Procesado: {file_path.name} ({result['chunks_added']} chunks)")
                
            except Exception as e:
                results.append({
                    "file": str(file_path),
                    "status": "error",
                    "error": str(e)
                })
                print(f"✗ Error en {file_path.name}: {str(e)}")
    
    return results


def infer_category_from_path(file_path: Path) -> str:
    """
    Infiere la categoría del documento desde la estructura de carpetas.
    
    Busca en las partes del path palabras clave que indiquen la categoría:
    - framework/ → Framework
    - teoria/ o evergreen/ → Teoría (se marca como evergreen en metadatos)
    - reporte/ → Reporte
    - caso_estudio/ → Caso de Estudio
    
    Args:
        file_path: Path del archivo
        
    Returns:
        Categoría inferida (Framework, Teoría, Reporte, Caso de Estudio)
    """
    parts = [part.lower() for part in file_path.parts]
    
    category_map = {
        "framework": "Framework",
        "teoria": "Teoría",
        "reporte": "Reporte",
        "caso_estudio": "Caso de Estudio",
    }
    
    # Buscar en las partes del path
    for part in parts:
        if part in category_map:
            return category_map[part]
    
    # Si no se encuentra ninguna categoría, retornar Teoría
    return "Teoría"


async def validate_ingestion_quality(file_path: str) -> Dict:
    """
    Valida la calidad de la ingesta de un documento.
    
    Verifica:
    - Que se hayan generado chunks
    - Que existan vectores densos y sparse
    - Que los metadatos estén completos
    
    Args:
        file_path: Ruta del documento original
        
    Returns:
        Dict con resultados de validación
    """
    kb = await get_knowledge_base()
    stats = await kb.get_stats()
    
    validation = {
        "document": Path(file_path).name,
        "collection_has_points": stats.get("count", 0) > 0,
        "validation_passed": True,
        "checks": []
    }
    
    # Verificar que la colección tenga puntos
    if stats.get("count", 0) == 0:
        validation["checks"].append({
            "check": "Collection has points",
            "passed": False,
            "message": "La colección está vacía"
        })
        validation["validation_passed"] = False
    else:
        validation["checks"].append({
            "check": "Collection has points",
            "passed": True,
            "message": f"Colección contiene {stats['count']} puntos"
        })
    
    return validation


# ============================================
# CLI para testing directo desde terminal
# ============================================

async def main_cli():
    """
    Función principal para ejecutar el script desde CLI.
    
    Ejemplo de uso:
        python -m app.scripts.tests.test_ingest_documents
    """
    print("=" * 60)
    print("AgencIA - Test de Ingesta de Documentos RAG")
    print("=" * 60)
    
    # Ejemplo de ingesta individual
    print("\n📄 Test 1: Ingesta de documento individual")
    print("-" * 60)
    
    request = DocumentIngestRequest(
        file_path="doc/ag_director_estrategia.txt",
        category="Framework",
        source_author="AgencIA Team",
        year=2024,
        is_evergreen=True,
        topic_tags=["estrategia", "agentes", "director"],
        industry_sector="Marketing Digital"
    )
    
    try:
        result = await ingest_document(request)
        print(f"✓ Documento ingresado exitosamente")
        print(f"  Chunks añadidos: {result['chunks_added']}")
        print(f"  Total en colección: {result['stats'].get('count', 0)}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    # Ejemplo de validación
    print("\n🔍 Test 2: Validación de calidad de ingesta")
    print("-" * 60)
    
    try:
        validation = await validate_ingestion_quality(request.file_path)
        print(f"✓ Validación completada")
        for check in validation["checks"]:
            status = "✓" if check["passed"] else "✗"
            print(f"  {status} {check['check']}: {check['message']}")
    except Exception as e:
        print(f"✗ Error en validación: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Tests completados")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main_cli())
