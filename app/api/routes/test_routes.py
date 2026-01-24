"""
AgencIA - Rutas de Testing RAG
===============================
Endpoints REST para testing de funcionalidades del sistema RAG.
"""

import traceback
from fastapi import APIRouter, HTTPException, status
from pathlib import Path
from typing import List

from app.api.models.ingest_models import (
    DocumentIngestRequest, 
    DocumentIngestResponse,
    BatchIngestResponse
)
from app.scripts.tests.test_ingest_documents import (
    ingest_document,
    scan_and_ingest_directory,
    validate_ingestion_quality
)


router = APIRouter(prefix="/api/test", tags=["Testing RAG"])


@router.post(
    "/ingest-document", 
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingestar documento individual al RAG",
    description="""
    Endpoint de testing para ingestar un documento individual al sistema RAG.
    
    **Funcionalidad probada:**
    - Extracción de texto del archivo
    - Chunking semántico automático
    - Generación de vectores densos (OpenAI text-embedding-3-large)
    - Generación de vectores sparse (BM25 con vocabulario personalizado)
    - Almacenamiento en Qdrant con metadatos estructurados
    
    **Metadatos personalizables:**
    - `category`: Framework, Teoría, Reporte, Caso de Estudio
    - `source_author`: Autor o fuente del documento
    - `year`: Año del documento (1900-2100)
    - `is_evergreen`: True para conocimiento permanente, False para temporal
    - `topic_tags`: Lista de tags de temas
    - `industry_sector`: Sector industrial relacionado
    
    **Respuesta:**
    - Cantidad de chunks generados y añadidos
    - Estadísticas actualizadas de la colección Qdrant
    - Metadatos utilizados en la ingesta
    """
)
async def test_ingest_document(request: DocumentIngestRequest):
    """
    Ingesta un documento individual al RAG con metadatos personalizados.
    """
    try:
        # Ejecutar ingesta
        result = await ingest_document(request)
        
        return DocumentIngestResponse(
            success=True,
            message=f"Documento ingresado exitosamente: {result['chunks_added']} chunks añadidos",
            file_path=request.file_path,
            chunks_added=result['chunks_added'],
            metadata=result['metadata_used'],
            collection_stats=result['stats']
        )
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archivo no encontrado: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de validación: {str(e)}"
        )
    except Exception as e:
        # Imprimir traceback completo en consola para debugging
        print("=" * 60)
        print("ERROR EN INGESTA DE DOCUMENTO:")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al ingestar documento: {str(e)}"
        )


@router.post(
    "/ingest-directory",
    response_model=BatchIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingesta masiva de carpeta completa",
    description="""
    Escanea recursivamente una carpeta e ingesta todos los documentos encontrados.
    
    **Características:**
    - Soporta archivos: .txt, .pdf, .docx
    - Inferencia automática de categoría desde estructura de carpetas
    - Procesamiento de múltiples archivos en secuencia
    - Reporte detallado de cada archivo procesado
    
    **Inferencia de categorías:**
    - `framework/` → Framework
    - `teoria/` o `evergreen/` → Teoría

    - `reporte/` → Reporte
    - `caso_estudio/` → Caso de Estudio
    - Otras carpetas → General
    """
)
async def test_ingest_directory(
    directory_path: str,
    source_author: str = "Unknown",
    year: int = 2024,
    is_evergreen: bool = False,
    topic_tags: List[str] = [],
    industry_sector: str = "General"
):
    """
    Ingesta masiva de documentos desde una carpeta.
    """
    try:
        from app.core.config import BASE_DIR
        
        # Validar que el directorio exista
        dir_path = Path(directory_path)
        
        # Convertir a ruta absoluta si es relativa
        if not dir_path.is_absolute():
            dir_path = BASE_DIR / directory_path
        
        if not dir_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directorio no encontrado: {directory_path}"
            )
        
        if not dir_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La ruta no es un directorio: {directory_path}"
            )
        
        # Metadatos por defecto
        default_metadata = {
            "source_author": source_author,
            "year": year,
            "is_evergreen": is_evergreen,
            "topic_tags": topic_tags,
            "industry_sector": industry_sector
        }
        
        # Ejecutar ingesta masiva
        results = await scan_and_ingest_directory(dir_path, default_metadata)
        
        # Calcular estadísticas
        total_chunks = sum(
            r.get("chunks_added", 0) 
            for r in results 
            if r.get("status") == "success"
        )
        
        # Obtener estadísticas finales de la colección
        from app.rag.knowledge_base import get_knowledge_base
        kb = await get_knowledge_base()
        final_stats = await kb.get_stats()
        
        return BatchIngestResponse(
            success=True,
            message=f"Ingesta masiva completada: {len(results)} archivos procesados",
            total_files=len(results),
            total_chunks=total_chunks,
            results=results,
            collection_stats=final_stats
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en ingesta masiva: {str(e)}"
        )


@router.get(
    "/validate-ingestion/{file_name}",
    summary="Validar calidad de ingesta",
    description="""
    Valida que un documento haya sido ingresado correctamente.
    
    **Verifica:**
    - Existencia de puntos en la colección
    - Presencia de vectores densos y sparse
    - Integridad de metadatos
    """
)
async def test_validate_ingestion(file_name: str):
    """
    Valida la calidad de la ingesta de un documento.
    """
    try:
        from app.core.config import BASE_DIR
        
        # Buscar archivo en las carpetas de documentos
        doc_path = BASE_DIR / "doc"
        
        # Buscar recursivamente
        found_files = list(doc_path.rglob(file_name))
        
        if not found_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Archivo no encontrado: {file_name}"
            )
        
        # Usar el primer archivo encontrado
        file_path = str(found_files[0])
        
        # Ejecutar validación
        validation = await validate_ingestion_quality(file_path)
        
        return validation
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en validación: {str(e)}"
        )


@router.get(
    "/collection-stats",
    summary="Obtener estadísticas de la colección",
    description="Retorna estadísticas actuales de la colección Qdrant"
)
async def get_collection_stats():
    """
    Obtiene estadísticas de la colección Qdrant.
    """
    try:
        from app.rag.knowledge_base import get_knowledge_base
        
        kb = await get_knowledge_base()
        final_stats = await kb.get_stats()
        
        return {
            "success": True,
            "stats": final_stats
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


@router.get(
    "/inspect-chunks",
    summary="Inspeccionar segmentación semántica",
    description="Permite ver cómo se dividen los chunks sin realizar la ingesta (sin gasto de API)"
)
async def test_inspect_chunks(file_path: str):
    """
    Analiza un documento y devuelve estadísticas de los chunks generados.
    """
    try:
        from app.core.config import BASE_DIR
        from app.rag.knowledge_base import get_knowledge_base
        
        path = Path(file_path)
        if not path.is_absolute():
            path = BASE_DIR / file_path
            
        if not path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        kb = await get_knowledge_base()
        texto = await kb.extract_text(str(path))
        chunks = kb.chunker.semantic_chunking(texto)
        
        inspection = []
        for i, chunk in enumerate(chunks):
            inspection.append({
                "chunk_id": i,
                "word_count": len(chunk.split()),
                "char_count": len(chunk),
                "preview": chunk[:200] + "..."
            })
            
        return {
            "file": path.name,
            "total_words": len(texto.split()),
            "num_chunks": len(chunks),
            "avg_words_per_chunk": len(texto.split()) / len(chunks) if chunks else 0,
            "chunks": inspection
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/test-rag-advanced",
    summary="Test RAG Avanzado",
    description="Test RAG Avanzado"
)
async def test_rag_advanced():
    """
    Test RAG Avanzado
    """
    import app.scripts.tests.test_rag_advanced as test_rag
    try:
        test_rag_results = await test_rag.test_rag()
        return {
            "success": True,
            "rag_advanced_results": test_rag_results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))