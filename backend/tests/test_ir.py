"""Pruebas de traducción de instrucciones semánticas a IR."""

from dataclasses import FrozenInstanceError

import pytest

from app.ir.generator import generar_ir
from app.ir.instructions import InstruccionIR, OpIR
from app.semantic.analyzer import Analizador
from app.semantic.symbol_table import DispositivoRepositoryMemoria, TablaSimbolos
from app.services.frontend_pipeline import analizar


def traducir(fuente: str) -> list[InstruccionIR]:
    """Analiza una fuente válida y traduce sus instrucciones semánticas."""
    resultado = analizar(fuente)
    assert not resultado.tiene_errores
    repositorio = DispositivoRepositoryMemoria()
    for simbolo in TablaSimbolos().listar():
        repositorio.registrar(simbolo)
    instrucciones, errores = Analizador(repositorio).analizar(resultado.programa)
    assert errores == []
    return generar_ir(instrucciones)


@pytest.mark.parametrize(
    ("fuente", "esperado"),
    [
        ("ENCENDER led1", [InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO"))]),
        ("APAGAR led1", [InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO"))]),
        ("ACTIVAR alarma1", [InstruccionIR(OpIR.SET_STATE, ("alarma1", "ACTIVADA"))]),
        ("DESACTIVAR alarma1", [InstruccionIR(OpIR.SET_STATE, ("alarma1", "DESACTIVADA"))]),
        ("CONSULTAR led1", [InstruccionIR(OpIR.GET_STATE, ("led1",))]),
        ("LISTAR DISPOSITIVOS", [InstruccionIR(OpIR.LIST_DEVICES)]),
        ('NOTIFICAR "Prueba"', [InstruccionIR(OpIR.NOTIFY, ("Prueba",))]),
        ('ENVIAR CORREO A "a@b.com" MENSAJE "Hola"',
         [InstruccionIR(OpIR.SEND_EMAIL, ("a@b.com", "Hola"))]),
        ("", []),
    ],
)
def test_traducciones(fuente: str, esperado: list[InstruccionIR]) -> None:
    """Cada instrucción se traduce con sus argumentos y HALT final."""
    assert traducir(fuente) == [*esperado, InstruccionIR(OpIR.HALT)]


def test_instrucciones_secuenciales() -> None:
    """El orden de comandos de un programa se conserva."""
    assert traducir("ENCENDER led1\nAPAGAR led1") == [
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.HALT),
    ]


def test_condicional_salta_al_halt() -> None:
    """La condición salta a la instrucción posterior al cuerpo."""
    assert traducir("SI led1 == ENCENDIDO ENTONCES APAGAR led1") == [
        InstruccionIR(OpIR.GET_STATE, ("led1",)),
        InstruccionIR(OpIR.COMPARE, ("led1", "==", "ENCENDIDO")),
        InstruccionIR(OpIR.JUMP_IF_FALSE, (4,)),
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.HALT),
    ]


def test_condicional_en_medio_salta_a_instruccion_siguiente() -> None:
    """El destino se calcula con el índice absoluto dentro de todo el programa."""
    assert traducir(
        'ENCENDER led2\nSI led1 == ENCENDIDO ENTONCES APAGAR led1\nNOTIFICAR "siguiente"'
    ) == [
        InstruccionIR(OpIR.SET_STATE, ("led2", "ENCENDIDO")),
        InstruccionIR(OpIR.GET_STATE, ("led1",)),
        InstruccionIR(OpIR.COMPARE, ("led1", "==", "ENCENDIDO")),
        InstruccionIR(OpIR.JUMP_IF_FALSE, (5,)),
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.NOTIFY, ("siguiente",)),
        InstruccionIR(OpIR.HALT),
    ]


def test_repeticion_expande_cuerpo() -> None:
    """Una repetición de tres acciones genera tres instrucciones de control."""
    assert traducir("REPETIR 3 VECES ENCENDER led1") == [
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
        InstruccionIR(OpIR.HALT),
    ]


def test_instruccion_inmutable_y_legible() -> None:
    """Una instrucción se muestra con sus argumentos y no puede modificarse."""
    instruccion = InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO"))
    assert str(instruccion) == "SET_STATE led1 ENCENDIDO"
    assert str(InstruccionIR(OpIR.HALT)) == "HALT"
    with pytest.raises(FrozenInstanceError):
        setattr(instruccion, "op", OpIR.HALT)


@pytest.mark.parametrize(
    "instruccion",
    [
        {"tipo": "DESCONOCIDO"},
        {"tipo": "CONTROL_DISPOSITIVO", "operacion": "DESCONOCIDA", "dispositivo": "led1"},
        {"tipo": "CONSULTA"},
        {"tipo": "REPETIR", "veces": 101, "accion": {"tipo": "LISTADO"}},
        {"tipo": "REPETIR", "veces": True, "accion": {"tipo": "LISTADO"}},
        {"tipo": "CONDICIONAL", "dispositivo": "led1", "estado": "APAGADO", "accion": []},
    ],
)
def test_entrada_invalida_se_informa(instruccion: dict[str, object]) -> None:
    """Una entrada que no cumple el contrato no genera IR incompleto."""
    with pytest.raises(ValueError):
        generar_ir([instruccion])
