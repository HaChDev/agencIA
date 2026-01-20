# Sistema de Testing Dinámico para RAG - Guía de Uso

Sistema completo para probar la ingesta de documentos al RAG con vectores densos (OpenAI) y sparse (BM25).

## 📁 Estructura Implementada

```
app/
├── api/
│   ├── models/
│   │   ├── __init__.py
│   │   └── ingest_models.py          ✓ Modelos Pydantic para validación
│   └── routes/
│       ├── __init__.py
│       └── test_routes.py            ✓ Endpoints REST de testing
├── scripts/
│   └── tests/
│       ├── __init__.py
│       └── test_ingest_documents.py  ✓ Script de testing dinámico
└── main.py                           ✓ Integración de rutas
```

---

## 🚀 Endpoints Disponibles

### 1. Ingesta de Documento Individual

**POST** `/api/test/ingest-document`

Ingesta un documento con metadatos personalizados.

**Body (JSON):**
```json
{
  "file_path": "doc/ag_director_estrategia.txt",
  "category": "framework",
  "source_author": "AgencIA Team",
  "year": 2024,
  "is_evergreen": true,
  "topic_tags": ["estrategia", "redes", "campañas"],
  "industry_sector": "Marketing Digital"
}
```

> **💡 Importante**: Usa **rutas relativas** al proyecto (ej: `doc/archivo.txt`) en lugar de rutas absolutas. El sistema funciona dentro de un contenedor Docker donde la ruta base es `/app`.

**Respuesta:**
```json
{
  "success": true,
  "message": "Documento ingresado exitosamente: 15 chunks añadidos",
  "file_path": "/app/doc/ag_director_estrategia.txt",
  "chunks_added": 15,
  "metadata": {
    "category": "Framework",
    "source_author": "AgencIA Team",
    "year": 2024,
    "is_evergreen": true,
    "topic_tags": ["estrategia", "redes", "campañas"],
    "industry_sector": "Marketing Digital"
  },
  "collection_stats": {
    "count": 15,
    "collection_name": "agencia_knowledge_base"
  }
}
```

---

### 2. Ingesta Masiva de Carpeta

**POST** `/api/test/ingest-directory?directory_path=doc/framework&source_author=AgencIA&year=2024`

Escanea recursivamente una carpeta e ingesta todos los archivos (.txt, .pdf, .docx).

**Parámetros Query:**
- `directory_path` (requerido): Ruta a la carpeta
- `source_author`: Autor por defecto
- `year`: Año por defecto
- `is_evergreen`: Si es conocimiento permanente
- `topic_tags`: Lista de tags (separados por coma)
- `industry_sector`: Sector industrial

**Respuesta:**
```json
{
  "success": true,
  "message": "Ingesta masiva completada: 5 archivos procesados",
  "total_files": 5,
  "total_chunks": 75,
  "results": [
    {
      "file": "c:/www/agencIA/doc/framework/ejemplo.txt",
      "status": "success",
      "chunks_added": 15,
      "category": "Framework",
      "metadata": {...}
    }
  ],
  "collection_stats": {...}
}
```

---

### 3. Validar Ingesta

**GET** `/api/test/validate-ingestion/{file_name}`

Valida que un documento haya sido ingresado correctamente.

**Ejemplo:** `/api/test/validate-ingestion/ag_director_estrategia.txt`

---

### 4. Estadísticas de Colección

**GET** `/api/test/collection-stats`

Obtiene estadísticas actuales de la colección Qdrant.

---

## 📝 Ejemplos de Uso con cURL

### Ejemplo 1: Documento Individual

```bash
curl -X POST "http://localhost:8000/api/test/ingest-document" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "doc/ag_director_estrategia.txt",
    "category": "framework",
    "source_author": "AgencIA Team",
    "year": 2024,
    "is_evergreen": true,
    "topic_tags": ["estrategia", "agentes", "director"],
    "industry_sector": "Marketing Digital"
  }'
```

> **📌 Nota**: Usa rutas relativas como `"doc/archivo.txt"`, no rutas absolutas de Windows.

### Ejemplo 2: Carpeta Completa

```bash
curl -X POST "http://localhost:8000/api/test/ingest-directory?directory_path=doc/framework&category=Framework&source_author=AgencIA&year=2024&is_evergreen=true"
```

### Ejemplo 3: Estadísticas

```bash
curl -X GET "http://localhost:8000/api/test/collection-stats"
```

---

## 🐍 Uso desde Python

```python
import httpx
import asyncio

async def test_ingest():
    async with httpx.AsyncClient() as client:
        # Ingestar documento
        response = await client.post(
            "http://localhost:8000/api/test/ingest-document",
            json={
                "file_path": "doc/ag_director_estrategia.txt",
                "category": "Framework",
                "source_author": "AgencIA Team",
                "year": 2024,
                "is_evergreen": True,
                "topic_tags": ["estrategia", "agentes"],
                "industry_sector": "Marketing Digital"
            }
        )
        
        result = response.json()
        print(f"Chunks añadidos: {result['chunks_added']}")
        print(f"Total en colección: {result['collection_stats']['count']}")

asyncio.run(test_ingest())
```

---

## 🔧 Uso del Script CLI

También puedes ejecutar el script directamente desde la terminal:

```bash
# Desde la raíz del proyecto
python -m app.scripts.tests.test_ingest_documents
```

Este ejecutará ejemplos de prueba predefinidos en la función `main_cli()`.

---

## 📊 Metadatos Personalizables

Todos los metadatos son configurables desde el request:

| Campo            | Tipo         | Descripción                                    | Requerido | Notas |
|------------------|--------------|------------------------------------------------|-----------|-------|
| `file_path`      | `string`     | Ruta al archivo (absoluta o relativa)         | ✓         | Se convierte automáticamente a absoluta |
| `category`       | `string`     | Framework, Teoría, Reporte, Caso de Estudio, Evergreen | ✓ | **Acepta variantes**: `teoria`, `teoría`, `caso_estudio`, etc. Se normaliza automáticamente |
| `source_author`  | `string`     | Autor o fuente del documento                   | ✓         | |
| `year`           | `integer`    | Año del documento (1900-2100)                  | ✓         | |
| `is_evergreen`   | `boolean`    | True para conocimiento permanente              |           | Default: `false` |
| `topic_tags`     | `string[]`   | Lista de tags de temas                         |           | Mejora recuperación híbrida |
| `industry_sector`| `string`     | Sector industrial relacionado                  |           | Default: `"General"` |

### ✨ Normalización Automática de Categorías

El sistema acepta **variantes comunes** de las categorías y las normaliza automáticamente:

- `"framework"`, `"Framework"` → **Framework**
- `"teoria"`, `"teoría"`, `"Teoría"` → **Teoría**
- `"reporte"`, `"Reporte"` → **Reporte**
- `"caso de estudio"`, `"caso_estudio"`, `"Caso de Estudio"` → **Caso de Estudio**
- `"evergreen"`, `"Evergreen"` → **Evergreen**
- `"general"`, `"General"` → **General**

**Ejemplo:** Puedes enviar `"categoria": "teoria"` y se guardará como `"Teoría"` automáticamente.

---

## 🎯 Inferencia Automática de Categorías

Al usar `/ingest-directory`, el sistema infiere automáticamente la categoría desde la estructura de carpetas:

| Carpeta         | Categoría Inferida  |
|-----------------|---------------------|
| `framework/`    | Framework           |
| `teoria/`       | Teoría              |
| `evergreen/`    | Evergreen           |
| `reporte/`      | Reporte             |
| `caso_estudio/` | Caso de Estudio     |
| Otras           | General             |

---

## ✅ Validaciones Implementadas

- **Existencia de archivo**: Valida que el archivo exista antes de ingestar
- **Categoría válida**: Solo acepta categorías predefinidas
- **Rango de año**: 1900-2100
- **Tipo de archivo**: Soporta .txt, .pdf, .docx
- **Generación de vectores**: Valida que se generen ambos vectores (denso y sparse)

---

## 🔍 Qué se Prueba con Cada Ingesta

1. ✅ **Extracción de texto** del archivo
2. ✅ **Chunking semántico** automático con `SemanticChunker`
3. ✅ **Vector denso** generado con OpenAI `text-embedding-3-large` (3072 dimensiones)
4. ✅ **Vector sparse** generado con BM25 personalizado (vocabulario de marketing)
5. ✅ **Almacenamiento en Qdrant** con ambos vectores (`semantic` y `keywords`)
6. ✅ **Metadatos estructurados** en el payload de cada punto
7. ✅ **Estadísticas actualizadas** de la colección

---

## 🐛 Troubleshooting

### Error: "Archivo no encontrado"
- Verifica que la ruta sea correcta
- Usa rutas relativas desde `c:/www/agencIA/` o absolutas

### Error: "La colección está vacía"
- Asegúrate de que Qdrant esté corriendo: `docker-compose up -d qdrant`
- Verifica la conexión en `docker-compose logs qdrant`

### Error: "OpenAI API Key"
- Verifica que `OPENAI_API_KEY` esté en el `.env`
- Restart la aplicación después de modificar el `.env`

---

## 📚 Documentación OpenAPI

Una vez iniciada la aplicación, accede a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Allí encontrarás la documentación interactiva de todos los endpoints con ejemplos.
