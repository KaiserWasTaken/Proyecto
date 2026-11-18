"""Tipos y representación de los tokens del lenguaje CommandFlow."""

from dataclasses import dataclass
from enum import StrEnum


class TipoToken(StrEnum):
    """Categorías léxicas, incluidas las palabras reservadas en mayúsculas."""

    ENCENDER = "ENCENDER"
    APAGAR = "APAGAR"
    ACTIVAR = "ACTIVAR"
    DESACTIVAR = "DESACTIVAR"
    CONSULTAR = "CONSULTAR"
    LISTAR = "LISTAR"
    DISPOSITIVOS = "DISPOSITIVOS"
    NOTIFICAR = "NOTIFICAR"
    ENVIAR = "ENVIAR"
    CORREO = "CORREO"
    A = "A"
    MENSAJE = "MENSAJE"
    SI = "SI"
    ENTONCES = "ENTONCES"
    REPETIR = "REPETIR"
    VECES = "VECES"
    ENCENDIDO = "ENCENDIDO"
    APAGADO = "APAGADO"
    ACTIVADA = "ACTIVADA"
    DESACTIVADA = "DESACTIVADA"
    IDENTIFICADOR = "IDENTIFICADOR"
    CADENA = "CADENA"
    NUMERO = "NUMERO"
    IGUAL_IGUAL = "IGUAL_IGUAL"
    SALTO_LINEA = "SALTO_LINEA"
    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    """Token inmutable con posición de inicio, en línea y columna de base 1.

    ``lexema`` conserva el texto original. ``valor`` contiene el identificador
    o la cadena interpretada como texto, el número como entero, o ``None``
    para tokens sin valor propio, incluidas las palabras reservadas.
    """

    tipo: TipoToken
    lexema: str
    valor: str | int | None
    linea: int
    columna: int
