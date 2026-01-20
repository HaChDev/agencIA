"""
AgencIA - Core Module Init
===========================
Exporta los componentes core de la aplicación.
"""

from app.core.config import settings, get_settings, Settings
# from app.core.memory import MemoryService, get_memory_service


__all__ = [
    "settings",
    "get_settings",
    "Settings",
    # "MemoryService",
    # "get_memory_service",
]
