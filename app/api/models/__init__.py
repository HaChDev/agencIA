"""
AgencIA - API Models
====================
Modelos Pydantic para requests y responses de la API.
"""

from .ingest_models import DocumentIngestRequest, DocumentIngestResponse

__all__ = [
    "DocumentIngestRequest",
    "DocumentIngestResponse"
]
