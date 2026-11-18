"""Nodos inmutables del árbol de sintaxis abstracta de CommandFlow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar


T = TypeVar("T")


class Operacion(StrEnum):
    """Operaciones de control de dispositivos."""

    ENCENDER = "ENCENDER"
    APAGAR = "APAGAR"
    ACTIVAR = "ACTIVAR"
    DESACTIVAR = "DESACTIVAR"


class NodoVisitor(ABC, Generic[T]):
    """Contrato de visitante con un método por tipo de nodo."""

    @abstractmethod
    def visit_programa(self, nodo: Programa) -> T:
        """Visita un programa."""

    @abstractmethod
    def visit_control_dispositivo(self, nodo: ControlDispositivo) -> T:
        """Visita una operación de control."""

    @abstractmethod
    def visit_consultar(self, nodo: Consultar) -> T:
        """Visita una consulta de dispositivo."""

    @abstractmethod
    def visit_listar(self, nodo: Listar) -> T:
        """Visita una instrucción de listado."""

    @abstractmethod
    def visit_notificar(self, nodo: Notificar) -> T:
        """Visita una notificación."""

    @abstractmethod
    def visit_enviar_correo(self, nodo: EnviarCorreo) -> T:
        """Visita un envío de correo."""

    @abstractmethod
    def visit_condicional(self, nodo: Condicional) -> T:
        """Visita una instrucción condicional."""

    @abstractmethod
    def visit_repetir(self, nodo: Repetir) -> T:
        """Visita una instrucción de repetición."""


@dataclass(frozen=True)
class Nodo(ABC):
    """Nodo abstracto situado en una línea y columna de base 1."""

    linea: int
    columna: int

    @abstractmethod
    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha el nodo al método correspondiente del visitante."""

    @abstractmethod
    def to_dict(self) -> dict[str, object]:
        """Representa el nodo como datos serializables en JSON."""

    def _datos_base(self) -> dict[str, object]:
        """Devuelve el tipo y la posición comunes de un nodo."""
        return {"tipo": type(self).__name__, "linea": self.linea, "columna": self.columna}


@dataclass(frozen=True)
class Programa(Nodo):
    """Programa con una secuencia inmutable de instrucciones."""

    instrucciones: tuple[Instruccion, ...]

    def __post_init__(self) -> None:
        """Rechaza colecciones mutables como lista de instrucciones."""
        if not isinstance(self.instrucciones, tuple):
            raise TypeError("Las instrucciones del programa deben ser una tupla")

    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha el programa al visitante."""
        return visitor.visit_programa(self)

    def to_dict(self) -> dict[str, object]:
        """Serializa las instrucciones del programa recursivamente."""
        return {**self._datos_base(), "instrucciones": [nodo.to_dict() for nodo in self.instrucciones]}


@dataclass(frozen=True)
class ControlDispositivo(Nodo):
    """Operación de control aplicada a un dispositivo."""

    operacion: Operacion
    dispositivo: str

    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha el control de dispositivo al visitante."""
        return visitor.visit_control_dispositivo(self)

    def to_dict(self) -> dict[str, object]:
        """Serializa la operación por nombre y el identificador."""
        return {**self._datos_base(), "operacion": self.operacion.name, "dispositivo": self.dispositivo}


@dataclass(frozen=True)
class Consultar(Nodo):
    """Consulta del estado de un dispositivo."""

    dispositivo: str

    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha la consulta al visitante."""
        return visitor.visit_consultar(self)

    def to_dict(self) -> dict[str, object]:
        """Serializa la consulta."""
        return {**self._datos_base(), "dispositivo": self.dispositivo}


@dataclass(frozen=True)
class Listar(Nodo):
    """Listado de dispositivos."""

    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha el listado al visitante."""
        return visitor.visit_listar(self)

    def to_dict(self) -> dict[str, object]:
        """Serializa el listado."""
        return self._datos_base()


@dataclass(frozen=True)
class Notificar(Nodo):
    """Notificación con un mensaje textual."""

    mensaje: str

    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha la notificación al visitante."""
        return visitor.visit_notificar(self)

    def to_dict(self) -> dict[str, object]:
        """Serializa la notificación."""
        return {**self._datos_base(), "mensaje": self.mensaje}


@dataclass(frozen=True)
class EnviarCorreo(Nodo):
    """Envío de un mensaje a un destinatario."""

    destinatario: str
    mensaje: str

    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha el envío de correo al visitante."""
        return visitor.visit_enviar_correo(self)

    def to_dict(self) -> dict[str, object]:
        """Serializa el destinatario y el mensaje."""
        return {**self._datos_base(), "destinatario": self.destinatario, "mensaje": self.mensaje}


InstruccionSimple = ControlDispositivo | Consultar | Listar | Notificar | EnviarCorreo
"""Instrucciones permitidas como cuerpo de SI y REPETIR."""


@dataclass(frozen=True)
class Condicional(Nodo):
    """Comparación de un estado y acción simple condicionada."""

    dispositivo: str
    estado: str
    accion: InstruccionSimple

    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha el condicional al visitante."""
        return visitor.visit_condicional(self)

    def to_dict(self) -> dict[str, object]:
        """Serializa la condición y su acción recursivamente."""
        return {
            **self._datos_base(),
            "dispositivo": self.dispositivo,
            "estado": self.estado,
            "accion": self.accion.to_dict(),
        }


@dataclass(frozen=True)
class Repetir(Nodo):
    """Repetición de una acción simple."""

    veces: int
    accion: InstruccionSimple

    def accept(self, visitor: NodoVisitor[T]) -> T:
        """Despacha la repetición al visitante."""
        return visitor.visit_repetir(self)

    def to_dict(self) -> dict[str, object]:
        """Serializa la cantidad y su acción recursivamente."""
        return {**self._datos_base(), "veces": self.veces, "accion": self.accion.to_dict()}


Instruccion = InstruccionSimple | Condicional | Repetir
"""Todos los tipos de instrucción aceptados en un programa."""
