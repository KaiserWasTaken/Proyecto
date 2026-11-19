"""Pruebas de los diagnósticos y el análisis sintáctico."""

import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.ast.nodes import (
    Condicional,
    Consultar,
    ControlDispositivo,
    EnviarCorreo,
    Instruccion,
    InstruccionSimple,
    Listar,
    Notificar,
    Operacion,
    Programa,
    Repetir,
)
from app.lexer.lexer import Lexer
from app.lexer.tokens import TipoToken, Token
from app.parser.errors import ErrorSintactico
from app.parser.parser import Parser


def test_error_sintactico_es_inmutable_y_se_formatea() -> None:
    """El diagnóstico conserva su código, posición y mensaje sin permitir cambios."""
    error = ErrorSintactico("ESPERABA_IDENTIFICADOR", "Se esperaba un identificador", 2, 9)

    assert error.codigo == "ESPERABA_IDENTIFICADOR"
    assert str(error) == "Error sintáctico (línea 2, col 9): Se esperaba un identificador"
    with pytest.raises(FrozenInstanceError):
        setattr(error, "linea", 3)


@pytest.mark.parametrize(
    ("fuente", "esperada"),
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
        (
            "REPETIR 3 VECES ENCENDER led1",
            Repetir(1, 1, 3, ControlDispositivo(1, 17, Operacion.ENCENDER, "led1")),
        ),
    ],
)
def test_instrucciones_validas(fuente: str, esperada: Instruccion) -> None:
    """Cada instrucción produce el árbol exacto con su posición."""
    tokens, errores_lexicos = Lexer(fuente).tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores_lexicos == []
    assert errores == []
    assert programa == Programa(1, 1, (esperada,))


@pytest.mark.parametrize(
    ("fuente", "codigo", "columna", "mensaje"),
    [
        ("ENCENDER", "ESPERABA_IDENTIFICADOR", 9,
         "Se esperaba un identificador de dispositivo después de ENCENDER, pero se encontró fin de línea"),
        ("ENCENDER led1 led2", "TOKENS_SOBRANTES", 15, "Se esperaba fin de línea, pero se encontró 'led2'"),
        ("LISTAR led1", "ESPERABA_PALABRA", 8, "Se esperaba DISPOSITIVOS después de LISTAR, pero se encontró 'led1'"),
        ("encender led1", "INSTRUCCION_DESCONOCIDA", 1, "Se esperaba una instrucción, pero se encontró 'encender'"),
        ("SI led1 ENCENDIDO ENTONCES APAGAR led1", "ESPERABA_OPERADOR", 9,
         "Se esperaba == después del dispositivo, pero se encontró 'ENCENDIDO'"),
        ("SI led1 == HOLA ENTONCES APAGAR led1", "ESPERABA_ESTADO", 12,
         "Se esperaba un estado después de ==, pero se encontró 'HOLA'"),
        ("SI led1 == ENCENDIDO APAGAR led1", "ESPERABA_PALABRA", 22,
         "Se esperaba ENTONCES después del estado, pero se encontró 'APAGAR'"),
        ("SI led1 == ENCENDIDO ENTONCES SI led2 == APAGADO ENTONCES APAGAR led1",
         "ANIDAMIENTO_NO_PERMITIDO", 31,
         "Se esperaba una instrucción simple sin anidamiento, pero se encontró 'SI'"),
        ("REPETIR VECES ENCENDER led1", "ESPERABA_NUMERO", 9,
         "Se esperaba un número después de REPETIR, pero se encontró 'VECES'"),
        ('ENVIAR CORREO A "a@b.com"', "ESPERABA_PALABRA", 26,
         "Se esperaba MENSAJE después del destinatario, pero se encontró fin de línea"),
        ("NOTIFICAR led1", "ESPERABA_CADENA", 11,
         "Se esperaba una cadena después de NOTIFICAR, pero se encontró 'led1'"),
    ],
)
def test_errores_por_linea(fuente: str, codigo: str, columna: int, mensaje: str) -> None:
    """Cada línea incorrecta produce un solo diagnóstico con posición precisa."""
    tokens, errores_lexicos = Lexer(fuente).tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores_lexicos == []
    assert programa == Programa(1, 1, ())
    assert errores == [ErrorSintactico(codigo, mensaje, 1, columna)]


@pytest.mark.parametrize(
    ("estado", "columna_accion"),
    [("ENCENDIDO", 34), ("APAGADO", 32), ("ACTIVADA", 33), ("DESACTIVADA", 36)],
)
def test_todos_los_estados_son_sintacticamente_validos(estado: str, columna_accion: int) -> None:
    """Los estados se aceptan sintácticamente sin evaluar tipos de dispositivos."""
    tokens, _ = Lexer(f"SI alarma1 == {estado} ENTONCES CONSULTAR alarma1").tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores == []
    assert programa == Programa(1, 1, (
        Condicional(1, 1, "alarma1", estado, Consultar(1, columna_accion, "alarma1")),
    ))


@pytest.mark.parametrize(
    ("accion", "esperada"),
    [
        ("APAGAR led1", ControlDispositivo(1, 17, Operacion.APAGAR, "led1")),
        ("CONSULTAR led1", Consultar(1, 17, "led1")),
        ("LISTAR DISPOSITIVOS", Listar(1, 17)),
        (r'NOTIFICAR "a\nb"', Notificar(1, 17, "a\nb")),
        ('ENVIAR CORREO A "a@b.com" MENSAJE "Hola"', EnviarCorreo(1, 17, "a@b.com", "Hola")),
    ],
)
def test_repetir_acepta_cualquier_instruccion_simple(accion: str, esperada: InstruccionSimple) -> None:
    """Cada clase de instrucción simple puede ser el cuerpo de REPETIR."""
    tokens, errores_lexicos = Lexer(f"REPETIR 2 VECES {accion}").tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores_lexicos == []
    assert errores == []
    assert programa.instrucciones == (Repetir(1, 1, 2, esperada),)


@pytest.mark.parametrize("fuente", ["ENCENDER dispositivo99", "ENCENDER alarma1", "REPETIR 0 VECES APAGAR led1"])
def test_no_aplica_validaciones_semanticas(fuente: str) -> None:
    """La existencia, compatibilidad y cantidad son responsabilidad semántica."""
    tokens, errores_lexicos = Lexer(fuente).tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores_lexicos == []
    assert errores == []
    assert len(programa.instrucciones) == 1


@pytest.mark.parametrize(
    ("fuente", "codigo", "columna"),
    [
        ("CONSULTAR", "ESPERABA_IDENTIFICADOR", 10),
        ("SI == APAGADO ENTONCES CONSULTAR led1", "ESPERABA_IDENTIFICADOR", 4),
        ("REPETIR 3 ENCENDER led1", "ESPERABA_PALABRA", 11),
        ("REPETIR 3 VECES REPETIR 2 VECES APAGAR led1", "ANIDAMIENTO_NO_PERMITIDO", 17),
        ("SI led1 == APAGADO ENTONCES REPETIR 2 VECES APAGAR led1", "ANIDAMIENTO_NO_PERMITIDO", 29),
        ('ENVIAR A "a@b.com" MENSAJE "x"', "ESPERABA_PALABRA", 8),
        ('ENVIAR CORREO "a@b.com" MENSAJE "x"', "ESPERABA_PALABRA", 15),
        ("ENVIAR CORREO A led1 MENSAJE \"x\"", "ESPERABA_CADENA", 17),
        ('ENVIAR CORREO A "a@b.com" MENSAJE led1', "ESPERABA_CADENA", 35),
    ],
)
def test_errores_en_reglas_adicionales(fuente: str, codigo: str, columna: int) -> None:
    """Las reglas restantes también rechazan tokens inesperados sin cascadas."""
    tokens, errores_lexicos = Lexer(fuente).tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores_lexicos == []
    assert programa.instrucciones == ()
    assert len(errores) == 1
    assert (errores[0].codigo, errores[0].linea, errores[0].columna) == (codigo, 1, columna)


def test_recuperacion_de_linea_con_instrucciones_validas() -> None:
    """Una línea inválida se descarta sin perder instrucciones posteriores."""
    tokens, errores_lexicos = Lexer("ENCENDER led1\nLISTAR led1 sobrante\nAPAGAR led1").tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores_lexicos == []
    assert programa == Programa(1, 1, (
        ControlDispositivo(1, 1, Operacion.ENCENDER, "led1"),
        ControlDispositivo(3, 1, Operacion.APAGAR, "led1"),
    ))
    assert len(errores) == 1
    assert (errores[0].codigo, errores[0].linea, errores[0].columna) == ("ESPERABA_PALABRA", 2, 8)


def test_acumula_errores_en_lineas_distintas() -> None:
    """Se acumula un diagnóstico por cada línea incorrecta."""
    tokens, _ = Lexer("ENCENDER\nLISTAR led1\nCONSULTAR led1").tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert programa == Programa(1, 1, (Consultar(3, 1, "led1"),))
    assert [(e.codigo, e.linea, e.columna) for e in errores] == [
        ("ESPERABA_IDENTIFICADOR", 1, 9), ("ESPERABA_PALABRA", 2, 8)
    ]


def test_lineas_en_blanco_y_comentarios() -> None:
    """Las posiciones reales se preservan al ignorar líneas sin instrucciones."""
    tokens, errores_lexicos = Lexer("\n # comentario\n  ENCENDER led1\n\n\tAPAGAR led1").tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores_lexicos == []
    assert errores == []
    assert programa == Programa(1, 1, (
        ControlDispositivo(3, 3, Operacion.ENCENDER, "led1"),
        ControlDispositivo(5, 2, Operacion.APAGAR, "led1"),
    ))


@pytest.mark.parametrize("fuente", ["", "# comentario", "\n\r\n# comentario\n"])
def test_programa_vacio(fuente: str) -> None:
    """Una fuente sin instrucciones produce un programa vacío."""
    tokens, errores_lexicos = Lexer(fuente).tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert errores_lexicos == []
    assert errores == []
    assert programa == Programa(1, 1, ())


def test_parser_recibe_tokens_aunque_haya_error_lexico() -> None:
    """Los errores léxicos se conservan aparte mientras se analizan los tokens."""
    tokens, errores_lexicos = Lexer("ENCENDER led1@").tokenizar()
    programa, errores = Parser(tokens).parsear()
    assert [(e.codigo, e.linea, e.columna) for e in errores_lexicos] == [
        ("CARACTER_NO_RECONOCIDO", 1, 14)
    ]
    assert errores == []
    assert programa == Programa(1, 1, (ControlDispositivo(1, 1, Operacion.ENCENDER, "led1"),))


def test_parser_termina_con_entradas_problematicas() -> None:
    """Un proceso aislado limita el tiempo de ejecución ante entradas extrañas."""
    codigo = """
from app.lexer.lexer import Lexer
from app.lexer.tokens import TipoToken, Token
from app.parser.parser import Parser
for texto in ('== == ==', '"hola', '\\n\\n', 'SI\\nREPETIR\\n=='):
    tokens, _ = Lexer(texto).tokenizar()
    Parser(tokens).parsear()
Parser([Token(TipoToken.EOF, '', None, 1, 1)]).parsear()
"""
    entorno = os.environ.copy()
    entorno["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    subprocess.run(
        [sys.executable, "-c", codigo],
        env=entorno,
        timeout=10,
        check=True,
        capture_output=True,
        text=True,
    )


def test_parser_exige_secuencia_terminada_en_eof() -> None:
    """Los tokens externos mal formados no se aceptan silenciosamente."""
    with pytest.raises(ValueError, match="terminar en EOF"):
        Parser([])
    eof = Token(TipoToken.EOF, "", None, 1, 1)
    with pytest.raises(ValueError, match="solo puede aparecer al final"):
        Parser([eof, eof])


def test_parsear_repetidamente() -> None:
    """Un segundo análisis no duplica errores ni instrucciones."""
    tokens, _ = Lexer("ENCENDER\nCONSULTAR led1").tokenizar()
    parser = Parser(tokens)
    assert parser.parsear() == parser.parsear()
