"""Esquemas HTTP de comandos y dispositivos."""

from typing import Literal

from pydantic import BaseModel, StrictStr


class SolicitudValidacion(BaseModel):
    """Fuente del programa que se desea validar."""

    source: StrictStr


class DispositivoRespuesta(BaseModel):
    """Información pública de un dispositivo."""

    identificador: str
    tipo: str
    estado: str
    operaciones: list[str]


class ErrorRespuesta(BaseModel):
    """Error de una fase del lenguaje."""

    fase: Literal["lexico", "sintactico", "semantico"]
    codigo: str
    mensaje: str
    linea: int
    columna: int


class ValidacionRespuesta(BaseModel):
    """Resultado de la validación del programa."""

    valido: bool
    errores: list[ErrorRespuesta]
    instrucciones: list[dict[str, object]]


class EventoRespuesta(BaseModel):
    """Evento de ejecución expuesto por la API."""

    tipo: str
    texto: str
    dispositivo: str | None = None
    estado: str | None = None


class EjecucionRespuesta(BaseModel):
    """Resultado de validación y ejecución de un programa."""

    valido: bool
    exito: bool
    errores: list[ErrorRespuesta]
    eventos: list[EventoRespuesta]
