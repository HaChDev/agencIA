"""
AgencIA - Modelos de Negocio
============================
Definición de tabla para Usuarios.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import String, DateTime, ForeignKey, Float, Enum as SQLEnum, JSON, Text, BigInteger, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



class User(Base):
    """Usuario de la agencia."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1), primary_key=True)
    user_name: Mapped[str] = mapped_column(String(150), nullable=False)
    user_lastname: Mapped[str] = mapped_column(String(150), nullable=False)
    user_fullname: Mapped[str] = mapped_column(String(150), nullable=False)
    docty_id: Mapped[int] = mapped_column(ForeignKey("document_types.id"), nullable=False) # tipo de documento
    user_doc_number: Mapped[str] = mapped_column(String(20)) # numero de documento
    user_email: Mapped[str] = mapped_column(String(150)) # correo electronico
    user_phone: Mapped[str] = mapped_column(String(15)) # telefono
    dipo_id: Mapped[int] = mapped_column(ForeignKey("politics_divisions.id"), nullable=False) # division politica
    user_address: Mapped[Optional[str]] = mapped_column(String(200)) # direccion
    industry_id: Mapped[int] = mapped_column(ForeignKey("industries.id"), nullable=False)
    user_website: Mapped[Optional[str]] = mapped_column(String(200))
    user_facebook: Mapped[Optional[str]] = mapped_column(String(200))
    user_instagram: Mapped[Optional[str]] = mapped_column(String(200))
    user_tiktok: Mapped[Optional[str]] = mapped_column(String(200))
    user_linkedin: Mapped[Optional[str]] = mapped_column(String(200))
    user_twitter: Mapped[Optional[str]] = mapped_column(String(200))
    user_youtube: Mapped[Optional[str]] = mapped_column(String(200))
    user_status: Mapped[str] = mapped_column(String(1), default="A")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    campaigns: Mapped[List["Campaign"]] = relationship(back_populates="user")
    politic_division: Mapped["PoliticDivision"] = relationship(back_populates="users")
    industry: Mapped["Industry"] = relationship(back_populates="users")
    document_type: Mapped["DocumentType"] = relationship(back_populates="users")
