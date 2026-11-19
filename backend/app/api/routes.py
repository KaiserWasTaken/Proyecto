"""Rutas HTTP de consulta de dispositivos y validación."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.schemas import DispositivoRespuesta, SolicitudValidacion, ValidacionRespuesta
from app.semantic.symbol_table import DispositivoRepository
from app.services.command_service import (
    DatosDispositivo,
    ResultadoValidacion,
    listar_dispositivos,
    validar_comandos,
)


router = APIRouter(prefix="/api")


def obtener_repositorio(request: Request) -> DispositivoRepository:
    """Obtiene el repositorio inicializado durante el ciclo de vida de la app."""
    repositorio = request.app.state.repositorio
    if not isinstance(repositorio, DispositivoRepository):
        raise TypeError("El repositorio de dispositivos no es válido")
    return repositorio


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
