"""Pruebas de integración entre el lexer y el parser."""

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
    Programa,
)
from app.lexer.tokens import TipoToken
from app.services.frontend_pipeline import analizar


@pytest.mark.parametrize(
    ("fuente", "instruccion"),
    [
        ("ENCENDER led1", ControlDispositivo(1, 1, Operacion.ENCENDER, "led1")),
        ("APAGAR led1", ControlDispositivo(1, 1, Operacion.APAGAR, "led1")),
        ("ACTIVAR alarma1", ControlDispositivo(1, 1, Operacion.ACTIVAR, "alarma1")),
        ("DESACTIVAR alarma1", ControlDispositivo(1, 1, Operacion.DESACTIVAR, "alarma1")),
        ("CONSULTAR led1", Consultar(1, 1, "led1")),
        ("LISTAR DISPOSITIVOS", Listar(1, 1)),
        ('NOTIFICAR "Prueba"', Notificar(1, 1, "Prueba")),
        ('ENVIAR CORREO A "a@b.com" MENSAJE "Hola"', EnviarCorreo(1, 1, "a@b.com", "Hola")),
        (
            "SI led1 == ENCENDIDO ENTONCES APAGAR led1",
            Condicional(1, 1, "led1", "ENCENDIDO", ControlDispositivo(1, 31, Operacion.APAGAR, "led1")),
        ),
        ("ENCENDER dispositivo99", ControlDispositivo(1, 1, Operacion.ENCENDER, "dispositivo99")),
        ("ENCENDER alarma1", ControlDispositivo(1, 1, Operacion.ENCENDER, "alarma1")),
    ],
)
def test_instrucciones_validas_sintacticamente(fuente: str, instruccion: Instruccion) -> None:
    """El análisis sintáctico no realiza validaciones semánticas."""
    resultado = analizar(fuente)
    assert not resultado.tiene_errores
    assert resultado.errores_lexicos == []
    assert resultado.errores_sintacticos == []
    assert resultado.programa == Programa(1, 1, (instruccion,))
    assert resultado.tokens[-1].tipo == TipoToken.EOF


def test_error_sintactico() -> None:
    """Una instrucción incompleta devuelve un error sintáctico."""
    resultado = analizar("ENCENDER")
    assert resultado.tiene_errores
    assert resultado.errores_lexicos == []
    assert len(resultado.errores_sintacticos) == 1
    assert resultado.errores_sintacticos[0].codigo == "ESPERABA_IDENTIFICADOR"
    assert resultado.programa.instrucciones == ()


def test_error_lexico_no_impide_el_parsing() -> None:
    """El AST se construye con los tokens restantes aunque haya un error léxico."""
    resultado = analizar("ENCENDER led1@")
    assert resultado.tiene_errores
    assert len(resultado.errores_lexicos) == 1
    assert resultado.errores_lexicos[0].codigo == "CARACTER_NO_RECONOCIDO"
    assert resultado.errores_sintacticos == []
    assert resultado.programa == Programa(
        1, 1, (ControlDispositivo(1, 1, Operacion.ENCENDER, "led1"),)
    )
