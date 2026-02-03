"""
AgencIA - Base Declarativa SQLAlchemy
=====================================
Clase base para todos los modelos ORM.
"""

from typing import Any
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    """
    Clase base para modelos SQLAlchemy con soporte async y dataclass.
    """
    pass
