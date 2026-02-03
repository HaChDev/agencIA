"""
AgencIA - Modelos de Negocio
============================
Definición de tabla para Industrias.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Float, Enum as SQLEnum, JSON, Text, BigInteger, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



class Industry(Base):
    """Industria de la agencia."""
    __tablename__ = "industries"
    
    id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1), primary_key=True)
    industry_name: Mapped[str] = mapped_column(String(150), nullable=False)
    industry_sector: Mapped[str] = mapped_column(String(150), nullable=False)
    industry_description: Mapped[str] = mapped_column(String(150), nullable=False)
    industry_status: Mapped[str] = mapped_column(String(1), default="A")
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relaciones
    campaigns: Mapped[List["Campaign"]] = relationship(back_populates="industries")
    users: Mapped[List["User"]] = relationship(back_populates="industries")
