"""Instrucciones de la representación intermedia de CommandFlow."""

from dataclasses import dataclass
from enum import StrEnum


class OpIR(StrEnum):
    """Operaciones intermedias que podrá ejecutar la máquina virtual.

    LIST_DEVICES representa el resultado observable de LISTAR DISPOSITIVOS,
    que no puede expresarse como una consulta de un dispositivo individual.
    """

    GET_STATE = "GET_STATE"
    SET_STATE = "SET_STATE"
    COMPARE = "COMPARE"
    JUMP_IF_FALSE = "JUMP_IF_FALSE"
    NOTIFY = "NOTIFY"
    SEND_EMAIL = "SEND_EMAIL"
    LIST_DEVICES = "LIST_DEVICES"
    HALT = "HALT"


@dataclass(frozen=True)
class InstruccionIR:
    """Operación y argumentos inmutables de una instrucción intermedia."""

    op: OpIR
    args: tuple[str | int, ...] = ()

    def __str__(self) -> str:
        """Representa la operación y sus argumentos en una línea."""
        return " ".join((self.op.value, *(str(arg) for arg in self.args)))
