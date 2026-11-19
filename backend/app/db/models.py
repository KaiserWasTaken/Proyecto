"""Modelos de persistencia del catálogo, notificaciones y ejecuciones."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Metadatos declarativos de las tres tablas."""


class DispositivoDB(Base):
    """Dispositivo persistido con identificador único."""

    __tablename__ = "dispositivos"

    identificador: Mapped[str] = mapped_column(String, primary_key=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False)


class NotificacionDB(Base):
    """Notificación registrada durante la ejecución."""

    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class EjecucionDB(Base):
    """Resultado persistido de una ejecución."""

    __tablename__ = "ejecuciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fuente: Mapped[str] = mapped_column(Text, nullable=False)
    exito: Mapped[bool] = mapped_column(Boolean, nullable=False)
    eventos: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
