"""Repositorios SQLAlchemy que participan en la transacción del llamador.

Reciben una sesión abierta y usan flush para hacer visibles sus cambios, pero
nunca hacen commit ni rollback: el servicio decide si confirma o revierte toda
la ejecución, incluidos los cambios de estado y las notificaciones.
"""

from dataclasses import replace
from sqlite3 import SQLITE_CONSTRAINT_PRIMARYKEY, SQLITE_CONSTRAINT_UNIQUE

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import DispositivoDB, EjecucionDB, NotificacionDB
from app.semantic.symbol_table import (
    DispositivoRepository,
    ErrorTablaSimbolos,
    Simbolo,
)
from app.vm.ports import RegistroNotificaciones


class PostgresDispositivoRepository(DispositivoRepository):
    """Repositorio de dispositivos sobre una sesión SQLAlchemy."""

    def __init__(self, sesion: Session) -> None:
        """Conserva la sesión inyectada por el llamador."""
        self._sesion = sesion

    def registrar(self, simbolo: Simbolo) -> None:
        """Registra un símbolo y comunica los identificadores duplicados."""
        mensaje = f"El dispositivo {simbolo.identificador} ya está registrado"
        if self._sesion.get(DispositivoDB, simbolo.identificador) is not None:
            raise ErrorTablaSimbolos("DISPOSITIVO_DUPLICADO", mensaje)
        try:
            self._sesion.add(DispositivoDB(
                identificador=simbolo.identificador, tipo=simbolo.tipo, estado=simbolo.estado
            ))
            self._sesion.flush()
        except IntegrityError as error:
            original = error.orig
            if (
                getattr(original, "sqlstate", None) == "23505"
                or getattr(original, "sqlite_errorcode", None)
                in (SQLITE_CONSTRAINT_PRIMARYKEY, SQLITE_CONSTRAINT_UNIQUE)
            ):
                raise ErrorTablaSimbolos("DISPOSITIVO_DUPLICADO", mensaje) from error
            raise

    def obtener(self, identificador: str) -> Simbolo | None:
        """Devuelve una instantánea inmutable o None si no existe."""
        fila = self._sesion.get(DispositivoDB, identificador)
        if fila is None:
            return None
        return Simbolo(fila.identificador, fila.tipo, fila.estado)

    def listar(self) -> list[Simbolo]:
        """Devuelve instantáneas de todos los dispositivos."""
        filas = self._sesion.scalars(select(DispositivoDB)).all()
        return [Simbolo(fila.identificador, fila.tipo, fila.estado) for fila in filas]

    def actualizar_estado(self, identificador: str, estado: str) -> None:
        """Valida el estado antes de actualizar la fila en la transacción actual."""
        fila = self._sesion.get(DispositivoDB, identificador)
        if fila is None:
            raise ErrorTablaSimbolos(
                "DISPOSITIVO_NO_EXISTE", f"El dispositivo {identificador} no existe"
            )
        actualizado = replace(Simbolo(fila.identificador, fila.tipo, fila.estado), estado=estado)
        fila.estado = actualizado.estado
        self._sesion.flush()


class PostgresRegistroNotificaciones(RegistroNotificaciones):
    """Registro de notificaciones en la transacción de la sesión."""

    def __init__(self, sesion: Session) -> None:
        """Conserva la sesión inyectada."""
        self._sesion = sesion

    def registrar(self, mensaje: str) -> None:
        """Añade una notificación sin confirmar la transacción."""
        self._sesion.add(NotificacionDB(mensaje=mensaje))
        self._sesion.flush()

    def listar(self) -> list[NotificacionDB]:
        """Devuelve las notificaciones en orden de registro."""
        return list(self._sesion.scalars(select(NotificacionDB).order_by(NotificacionDB.id)).all())


class RepositorioEjecuciones:
    """Historial de ejecuciones en la transacción de la sesión."""

    def __init__(self, sesion: Session) -> None:
        """Conserva la sesión inyectada."""
        self._sesion = sesion

    def guardar(self, fuente: str, exito: bool, eventos: list[dict[str, object]]) -> None:
        """Guarda el resultado serializable de una ejecución sin hacer commit."""
        self._sesion.add(EjecucionDB(fuente=fuente, exito=exito, eventos=eventos))
        self._sesion.flush()

    def listar_ultimas(self, n: int) -> list[EjecucionDB]:
        """Devuelve hasta n ejecuciones, de la más reciente a la más antigua."""
        if n < 0:
            raise ValueError("El número de ejecuciones no puede ser negativo")
        consulta = select(EjecucionDB).order_by(EjecucionDB.id.desc()).limit(n)
        return list(self._sesion.scalars(consulta).all())
