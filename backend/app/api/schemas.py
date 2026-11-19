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
