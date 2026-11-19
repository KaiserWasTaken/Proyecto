"""Rutas HTTP de dispositivos, validación y ejecución."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.schemas import (
    DispositivoRespuesta,
    EjecucionRespuesta,
    SolicitudValidacion,
    ValidacionRespuesta,
)
from app.db.repositorios import PostgresDispositivoRepository
from app.semantic.symbol_table import DispositivoRepository
from app.services.command_service import (
    DatosDispositivo,
    ResultadoComando,
    ResultadoValidacion,
    ejecutar_comandos,
    listar_dispositivos,
    validar_comandos,
)
from app.vm.ports import ServicioCorreo


router = APIRouter(prefix="/api")


def obtener_sesion(request: Request) -> Iterator[Session]:
    """Abre una sesión por petición y la cierra sin confirmar por defecto."""
    with request.app.state.fabrica_sesiones() as sesion:
        yield sesion


def obtener_correo(request: Request) -> ServicioCorreo:
    """Obtiene el servicio SMTP inicializado al arrancar."""
    correo = request.app.state.servicio_correo
    if not isinstance(correo, ServicioCorreo):
        raise TypeError("El servicio de correo no es válido")
    return correo


def obtener_repositorio(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> DispositivoRepository:
    """Construye el repositorio de dispositivos para la petición."""
    return PostgresDispositivoRepository(sesion)


@router.get("/devices", response_model=list[DispositivoRespuesta])
def consultar_dispositivos(
    repositorio: Annotated[DispositivoRepository, Depends(obtener_repositorio)],
) -> list[DatosDispositivo]:
    """Devuelve la lista actual de dispositivos."""
    return listar_dispositivos(repositorio)


@router.post("/commands/validate", response_model=ValidacionRespuesta)
def validar(
    solicitud: SolicitudValidacion,
    repositorio: Annotated[DispositivoRepository, Depends(obtener_repositorio)],
) -> ResultadoValidacion:
    """Valida instrucciones sin ejecutarlas."""
    return validar_comandos(solicitud.source, repositorio)


@router.post("/commands/execute", response_model=EjecucionRespuesta, response_model_exclude_none=True)
def ejecutar(
    solicitud: SolicitudValidacion,
    sesion: Annotated[Session, Depends(obtener_sesion)],
    correo: Annotated[ServicioCorreo, Depends(obtener_correo)],
) -> ResultadoComando:
    """Ejecuta un programa válido y devuelve sus eventos ordenados."""
    return ejecutar_comandos(solicitud.source, sesion, correo)
