"""
AgencIA - Modelos de Negocio
============================
Definición de tabla para Divisiones Políticas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Float, Enum as SQLEnum, JSON, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



class PoliticDivision(Base):
    """Divisiones políticas del país."""
    __tablename__ = "politics_divisions"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    department: Mapped[str] = mapped_column(String(150), nullable=False)
    municipality: Mapped[str] = mapped_column(String(150), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relaciones
    users: Mapped[List["User"]] = relationship(back_populates="politic_division")
