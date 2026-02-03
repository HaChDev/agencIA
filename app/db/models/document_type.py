"""
AgencIA - Modelos de Negocio
============================
Definición de tabla para Tipos de Documentos.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Float, Enum as SQLEnum, JSON, Text, BigInteger, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



class DocumentType(Base):
    """Tipo de documento de los usuarios."""
    __tablename__ = "document_types"
    
    id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1), primary_key=True)
    document_type_abbreviation: Mapped[str] = mapped_column(String(3), nullable=False)
    document_type_name: Mapped[str] = mapped_column(String(60), nullable=False)
    document_type_status: Mapped[str] = mapped_column(String(1), default="A")
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relaciones
    users: Mapped[List["User"]] = relationship(back_populates="document_types")
