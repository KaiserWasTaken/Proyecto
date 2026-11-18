"""Pruebas de serialización, visitantes e inmutabilidad del AST."""

import json
from collections import Counter
from dataclasses import FrozenInstanceError

import pytest

from app.ast.nodes import (
    Condicional,
    Consultar,
    ControlDispositivo,
    EnviarCorreo,
    Listar,
    Nodo,
    NodoVisitor,
    Notificar,
    Operacion,
    Programa,
    Repetir,
)


@pytest.mark.parametrize(
    ("nodo", "esperado"),
    [
        (Programa(1, 1, ()), {"instrucciones": []}),
        (ControlDispositivo(2, 3, Operacion.ENCENDER, "led1"),
         {"operacion": "ENCENDER", "dispositivo": "led1"}),
        (Consultar(3, 1, "led1"), {"dispositivo": "led1"}),
        (Listar(4, 1), {}),
        (Notificar(5, 1, "Prueba"), {"mensaje": "Prueba"}),
        (EnviarCorreo(6, 1, "a@b.com", "Hola"),
         {"destinatario": "a@b.com", "mensaje": "Hola"}),
        (Condicional(7, 1, "led1", "ENCENDIDO", Consultar(7, 27, "led1")),
         {"dispositivo": "led1", "estado": "ENCENDIDO",
          "accion": {"tipo": "Consultar", "linea": 7, "columna": 27, "dispositivo": "led1"}}),
        (Repetir(8, 1, 3, Notificar(8, 17, "Hola")),
         {"veces": 3, "accion": {"tipo": "Notificar", "linea": 8, "columna": 17, "mensaje": "Hola"}}),
    ],
)
def test_to_dict_serializable_y_completo(nodo: Nodo, esperado: dict[str, object]) -> None:
    """Cada nodo incluye su tipo, posición y atributos serializados."""
    datos = nodo.to_dict()
    assert datos == {
        "tipo": type(nodo).__name__,
        "linea": nodo.linea,
        "columna": nodo.columna,
        **esperado,
    }
    assert json.loads(json.dumps(datos)) == datos


class ContadorNodos(NodoVisitor[None]):
    """Visitante de prueba que recorre y cuenta los nodos de un programa."""

    def __init__(self) -> None:
        """Inicializa los contadores."""
        self.cantidades: Counter[str] = Counter()

    def visit_programa(self, nodo: Programa) -> None:
        """Cuenta el programa y recorre sus instrucciones."""
        self.cantidades["Programa"] += 1
        for instruccion in nodo.instrucciones:
            instruccion.accept(self)

    def visit_control_dispositivo(self, nodo: ControlDispositivo) -> None:
        """Cuenta un control de dispositivo."""
        self.cantidades["ControlDispositivo"] += 1

    def visit_consultar(self, nodo: Consultar) -> None:
        """Cuenta una consulta."""
        self.cantidades["Consultar"] += 1

    def visit_listar(self, nodo: Listar) -> None:
        """Cuenta un listado."""
        self.cantidades["Listar"] += 1

    def visit_notificar(self, nodo: Notificar) -> None:
        """Cuenta una notificación."""
        self.cantidades["Notificar"] += 1

    def visit_enviar_correo(self, nodo: EnviarCorreo) -> None:
        """Cuenta un envío de correo."""
        self.cantidades["EnviarCorreo"] += 1

    def visit_condicional(self, nodo: Condicional) -> None:
        """Cuenta el condicional y visita su acción."""
        self.cantidades["Condicional"] += 1
        nodo.accion.accept(self)

    def visit_repetir(self, nodo: Repetir) -> None:
        """Cuenta la repetición y visita su acción."""
        self.cantidades["Repetir"] += 1
        nodo.accion.accept(self)


def test_visitor_recorre_programa_y_acciones_anidadas() -> None:
    """El visitante recibe cada nodo del árbol, incluidos los hijos."""
    programa = Programa(1, 1, (
        Condicional(1, 1, "led1", "ENCENDIDO", ControlDispositivo(1, 28, Operacion.APAGAR, "led1")),
        Repetir(2, 1, 3, Notificar(2, 17, "Hola")),
        Consultar(3, 1, "led1"),
        Listar(4, 1),
        EnviarCorreo(5, 1, "a@b.com", "Hola"),
    ))
    contador = ContadorNodos()
    programa.accept(contador)
    assert contador.cantidades == Counter({
        "Programa": 1, "Condicional": 1, "ControlDispositivo": 1,
        "Repetir": 1, "Notificar": 1, "Consultar": 1, "Listar": 1,
        "EnviarCorreo": 1,
    })
    datos = programa.to_dict()
    assert json.loads(json.dumps(datos)) == datos
    instrucciones = datos["instrucciones"]
    assert isinstance(instrucciones, list)
    assert len(instrucciones) == 5


@pytest.mark.parametrize(
    "nodo",
    [
        Programa(1, 1, ()),
        ControlDispositivo(1, 1, Operacion.APAGAR, "led1"),
        Consultar(1, 1, "led1"),
        Listar(1, 1),
        Notificar(1, 1, "Hola"),
        EnviarCorreo(1, 1, "a@b.com", "Hola"),
        Condicional(1, 1, "led1", "ENCENDIDO", Consultar(1, 27, "led1")),
        Repetir(1, 1, 3, Consultar(1, 17, "led1")),
    ],
)
def test_nodos_son_inmutables(nodo: Nodo) -> None:
    """Los campos de cada nodo rechazan asignaciones."""
    with pytest.raises(FrozenInstanceError):
        setattr(nodo, "linea", 9)


def test_programa_rechaza_lista_mutable() -> None:
    """El programa exige una tupla de instrucciones."""
    with pytest.raises(TypeError, match="deben ser una tupla"):
        Programa(1, 1, [])  # type: ignore[arg-type]
