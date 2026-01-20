"""
AgencIA - Modelos de Ingesta
=============================
Modelos Pydantic para validar requests y responses de ingesta de documentos.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from pathlib import Path


class DocumentIngestRequest(BaseModel):
    """
    Request para ingestar un documento al RAG.
    
    Permite personalizar todos los metadatos que se almacenarán
    en Qdrant junto con los vectores densos y sparse.
    """
    
    file_path: str = Field(
        ..., 
        description="Ruta absoluta o relativa al archivo (desde raíz del proyecto)"
    )
    category: str = Field(
        ..., 
        description="Categoría del documento: Framework, Teoría, Reporte, Caso de Estudio, Evergreen"
    )
    source_author: str = Field(
        ..., 
        description="Autor o fuente del documento"
    )
    year: int = Field(
        ..., 
        description="Año del documento", 
        ge=1900, 
        le=2100
    )
    is_evergreen: bool = Field(
        default=False, 
        description="Si es conocimiento permanente (teorías, frameworks) o temporal (reportes)"
    )
    topic_tags: List[str] = Field(
        default_factory=list, 
        description="Tags de temas para mejorar la búsqueda"
    )
    industry_sector: str = Field(
        default="General", 
        description="Sector industrial relacionado"
    )
    
    @field_validator('file_path')
    @classmethod
    def validate_file_exists(cls, v: str) -> str:
        """
        Valida que el archivo exista, convirtiendo rutas relativas a absolutas.
        Funciona tanto en desarrollo local como dentro de contenedor Docker.
        """
        from app.core.config import BASE_DIR
        
        path = Path(v)
        
        # Si es ruta relativa, convertir a absoluta usando BASE_DIR del proyecto
        if not path.is_absolute():
            # BASE_DIR apunta a la raíz del proyecto (donde está app/)
            # Si la ruta empieza con 'doc/', usarla directamente
            # Si no, asumir que es relativa a BASE_DIR
            path = BASE_DIR / v
        
        # Intentar también desde la raíz del contenedor si la primera no funciona
        # (para compatibilidad con rutas como "c:/www/agencIA/doc/...")
        if not path.exists():
            # Intentar interpretando como ruta relativa al proyecto
            relative_path = Path(v)
            if str(relative_path).startswith('c:'):
                # Extraer la parte después de agencIA/
                parts = Path(v).parts
                if 'agencIA' in parts:
                    idx = parts.index('agencIA')
                    relative_parts = parts[idx + 1:]
                    path = BASE_DIR / Path(*relative_parts)
        
        # Validar existencia final
        if not path.exists():
            raise ValueError(f"El archivo no existe: {path}")
        
        if not path.is_file():
            raise ValueError(f"La ruta no es un archivo: {path}")
        
        return str(path)
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """
        Valida y normaliza la categoría.
        Acepta variantes sin tilde y en minúsculas, las normaliza al formato correcto.
        """
        # Mapeo de variantes aceptadas a formato correcto
        category_map = {
            # Framework
            "framework": "Framework",
            
            # Teoría
            "teoria": "Teoría",
            "teoría": "Teoría",
            
            # Reporte
            "reporte": "Reporte",
            
            # Caso de Estudio
            "caso de estudio": "Caso de Estudio",
            "caso_estudio": "Caso de Estudio",
            "casoestudio": "Caso de Estudio",
        }
        
        # Normalizar entrada (lowercase para comparación)
        v_lower = v.lower()
        
        # Si está en el mapeo, retornar el formato correcto
        if v_lower in category_map:
            return category_map[v_lower]
        
        # Si ya está en formato correcto, retornar tal cual
        valid_categories = ["Framework", "Teoría", "Reporte", "Caso de Estudio"]
        if v in valid_categories:
            return v
        
        # Si no coincide con ninguna, levantar error
        raise ValueError(
            f"Categoría inválida: '{v}'. "
            f"Categorías válidas: {', '.join(valid_categories)}"
        )



class DocumentIngestResponse(BaseModel):
    """
    Response de ingesta de documento con estadísticas detalladas.
    """
    
    success: bool = Field(
        ..., 
        description="Si la ingesta fue exitosa"
    )
    message: str = Field(
        ..., 
        description="Mensaje descriptivo del resultado"
    )
    file_path: str = Field(
        ..., 
        description="Ruta del archivo procesado"
    )
    chunks_added: int = Field(
        ..., 
        description="Cantidad de chunks (fragmentos) añadidos a Qdrant"
    )
    metadata: dict = Field(
        ..., 
        description="Metadatos utilizados en la ingesta"
    )
    collection_stats: Optional[dict] = Field(
        None, 
        description="Estadísticas de la colección después de la ingesta"
    )


class BatchIngestResponse(BaseModel):
    """
    Response para ingesta masiva de múltiples documentos.
    """
    
    success: bool = Field(
        ..., 
        description="Si la ingesta masiva fue exitosa"
    )
    message: str = Field(
        ..., 
        description="Resumen de la operación"
    )
    total_files: int = Field(
        ..., 
        description="Total de archivos procesados"
    )
    total_chunks: int = Field(
        ..., 
        description="Total de chunks añadidos"
    )
    results: List[dict] = Field(
        default_factory=list, 
        description="Resultados detallados por archivo"
    )
    collection_stats: Optional[dict] = Field(
        None, 
        description="Estadísticas finales de la colección"
    )
