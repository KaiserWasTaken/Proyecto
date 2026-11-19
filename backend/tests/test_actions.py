"""Pruebas de las acciones semánticas independientes del analizador."""

import pytest

from app.ast.nodes import (
    Condicional,
    Consultar,
    ControlDispositivo,
    EnviarCorreo,
    Instruccion,
    Listar,
    Notificar,
    Operacion,
    Repetir,
)
from app.semantic.actions import (
    construir_instruccion,
    verificar_dispositivo,
    verificar_estado,
    verificar_operacion,
)
from app.semantic.symbol_table import ErrorTablaSimbolos, TablaSimbolos


def test_verificaciones_solo_leen_tabla() -> None:
    """Las consultas distinguen identificadores y tipos sin modificar estados."""
    tabla = TablaSimbolos()
    inicial = tabla.listar()
    assert verificar_dispositivo("led1", tabla)
    assert not verificar_dispositivo("LED1", tabla)
    assert verificar_operacion("ENCENDER", "led1", tabla)
    assert not verificar_operacion("ENCENDER", "alarma1", tabla)
    assert verificar_estado("alarma1", "ACTIVADA", tabla)
    assert not verificar_estado("alarma1", "ENCENDIDO", tabla)
    assert tabla.listar() == inicial


@pytest.mark.parametrize("verificacion", ["operacion", "estado"])
def test_verificaciones_rechazan_dispositivo_ausente(verificacion: str) -> None:
    """Una ausencia no se confunde con una incompatibilidad."""
    tabla = TablaSimbolos()
    with pytest.raises(ErrorTablaSimbolos) as error:
        if verificacion == "operacion":
            verificar_operacion("ENCENDER", "LED1", tabla)
        else:
            verificar_estado("LED1", "ENCENDIDO", tabla)
    assert error.value.codigo == "DISPOSITIVO_NO_EXISTE"


@pytest.mark.parametrize(
    ("nodo", "esperado"),
    [
        (ControlDispositivo(1, 1, Operacion.ENCENDER, "led1"),
         {"tipo": "CONTROL_DISPOSITIVO", "operacion": "ENCENDER", "dispositivo": "led1"}),
        (Consultar(1, 1, "led1"), {"tipo": "CONSULTA", "dispositivo": "led1"}),
        (Listar(1, 1), {"tipo": "LISTADO"}),
        (Notificar(1, 1, "Prueba"), {"tipo": "NOTIFICACION", "mensaje": "Prueba"}),
        (EnviarCorreo(1, 1, "a@b.com", "Hola"),
         {"tipo": "CORREO", "destinatario": "a@b.com", "mensaje": "Hola"}),
        (Condicional(1, 1, "led1", "ENCENDIDO", ControlDispositivo(1, 31, Operacion.APAGAR, "led1")),
         {"tipo": "CONDICIONAL", "dispositivo": "led1", "estado": "ENCENDIDO",
          "accion": {"tipo": "CONTROL_DISPOSITIVO", "operacion": "APAGAR", "dispositivo": "led1"}}),
        (Repetir(1, 1, 3, Consultar(1, 17, "led1")),
         {"tipo": "REPETIR", "veces": 3, "accion": {"tipo": "CONSULTA", "dispositivo": "led1"}}),
    ],
)
def test_construir_instruccion(nodo: Instruccion, esperado: dict[str, object]) -> None:
    """Cada nodo se convierte al diccionario especificado, incluidos sus hijos."""
    assert construir_instruccion(nodo) == esperado
