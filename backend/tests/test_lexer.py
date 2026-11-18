"""Pruebas del análisis léxico y de su recuperación ante errores."""

import pytest

from app.lexer.errors import ErrorLexico
from app.lexer.lexer import Lexer
from app.lexer.tokens import TipoToken, Token


def test_encender_identificador_y_posiciones() -> None:
    """Reconoce un comando y conserva las posiciones de sus tokens."""
    tokens, errores = Lexer("ENCENDER led1").tokenizar()
    assert errores == []
    assert tokens == [
        Token(TipoToken.ENCENDER, "ENCENDER", None, 1, 1),
        Token(TipoToken.IDENTIFICADOR, "led1", "led1", 1, 10),
        Token(TipoToken.EOF, "", None, 1, 14),
    ]


@pytest.mark.parametrize(
    ("fuente", "tipos"),
    [
        ("LISTAR DISPOSITIVOS", [TipoToken.LISTAR, TipoToken.DISPOSITIVOS]),
        (
            "SI led1 == ENCENDIDO ENTONCES APAGAR led1",
            [
                TipoToken.SI, TipoToken.IDENTIFICADOR, TipoToken.IGUAL_IGUAL,
                TipoToken.ENCENDIDO, TipoToken.ENTONCES, TipoToken.APAGAR,
                TipoToken.IDENTIFICADOR,
            ],
        ),
        (
            'ENVIAR CORREO A "a@b.com" MENSAJE "Hola"',
            [
                TipoToken.ENVIAR, TipoToken.CORREO, TipoToken.A, TipoToken.CADENA,
                TipoToken.MENSAJE, TipoToken.CADENA,
            ],
        ),
    ],
)
def test_secuencias_de_comandos(fuente: str, tipos: list[TipoToken]) -> None:
    """Reconoce las secuencias de tokens de instrucciones representativas."""
    tokens, errores = Lexer(fuente).tokenizar()
    assert errores == []
    assert [token.tipo for token in tokens] == tipos + [TipoToken.EOF]
    if fuente.startswith("ENVIAR"):
        assert tokens[3].valor == "a@b.com"
        assert tokens[5].valor == "Hola"


def test_caracter_no_reconocido_conserva_tokens() -> None:
    """Un carácter no reconocido se omite e informa su posición exacta."""
    tokens, errores = Lexer("ENCENDER led1@").tokenizar()
    assert [t.tipo for t in tokens] == [
        TipoToken.ENCENDER, TipoToken.IDENTIFICADOR, TipoToken.EOF
    ]
    assert tokens[1].lexema == "led1"
    assert errores == [ErrorLexico("CARACTER_NO_RECONOCIDO", "Carácter '@' no reconocido", 1, 14)]
    assert str(errores[0]) == "Error léxico (línea 1, col 14): Carácter '@' no reconocido"
    assert (tokens[-1].linea, tokens[-1].columna) == (1, 15)


def test_cadena_con_escapes() -> None:
    """Las comillas, la barra invertida y el salto escapados se interpretan."""
    fuente = r'NOTIFICAR "dijo \"hola\"\\\nfin"'
    tokens, errores = Lexer(fuente).tokenizar()
    assert errores == []
    assert tokens[1] == Token(
        TipoToken.CADENA, r'"dijo \"hola\"\\\nfin"', 'dijo "hola"\\\nfin', 1, 11
    )


@pytest.mark.parametrize("final", ["\n", "\r\n", ""])
def test_cadena_sin_cerrar_se_recupera(final: str) -> None:
    """Una cadena sin cerrar se descarta y no consume el salto de línea."""
    resto = "APAGAR led1" if final else ""
    tokens, errores = Lexer('NOTIFICAR "sin cerrar' + final + resto).tokenizar()
    assert errores == [ErrorLexico("CADENA_SIN_CERRAR", "Cadena sin cerrar", 1, 11)]
    assert all(t.tipo != TipoToken.CADENA for t in tokens)
    if final:
        assert [(t.tipo, t.linea, t.columna) for t in tokens[1:]] == [
            (TipoToken.SALTO_LINEA, 1, 22),
            (TipoToken.APAGAR, 2, 1),
            (TipoToken.IDENTIFICADOR, 2, 8),
            (TipoToken.EOF, 2, 12),
        ]


def test_escape_invalido_continua_y_conserva_caracter() -> None:
    """Los escapes inválidos notifican la barra y conservan el carácter escapado."""
    tokens, errores = Lexer(r'NOTIFICAR "a\qb"').tokenizar()
    assert tokens[1].valor == "aqb"
    assert tokens[1].lexema == r'"a\qb"'
    assert errores == [ErrorLexico("ESCAPE_INVALIDO", r"Secuencia de escape '\q' no válida", 1, 13)]


def test_escape_incompleto_al_final_de_linea() -> None:
    """Una barra antes del salto no consume la siguiente línea."""
    tokens, errores = Lexer('NOTIFICAR "x\\\nENCENDER led1').tokenizar()
    assert [error.codigo for error in errores] == ["CADENA_SIN_CERRAR"]
    assert [token.tipo for token in tokens] == [
        TipoToken.NOTIFICAR, TipoToken.SALTO_LINEA, TipoToken.ENCENDER,
        TipoToken.IDENTIFICADOR, TipoToken.EOF,
    ]


def test_igual_suelto_y_operador() -> None:
    """Un igual aislado produce error mientras == produce un token."""
    tokens, errores = Lexer("= ==").tokenizar()
    assert errores == [ErrorLexico("IGUAL_SUELTO", "Signo '=' sin pareja", 1, 1)]
    assert tokens == [
        Token(TipoToken.IGUAL_IGUAL, "==", None, 1, 3),
        Token(TipoToken.EOF, "", None, 1, 5),
    ]


def test_lineas_en_blanco_y_comentarios() -> None:
    """Los comentarios se omiten, pero se conservan todos los saltos."""
    tokens, errores = Lexer("ENCENDER led1 # comentario\n\n# otro\nAPAGAR led1").tokenizar()
    assert errores == []
    assert [(t.tipo, t.linea, t.columna) for t in tokens] == [
        (TipoToken.ENCENDER, 1, 1), (TipoToken.IDENTIFICADOR, 1, 10),
        (TipoToken.SALTO_LINEA, 1, 27), (TipoToken.SALTO_LINEA, 2, 1),
        (TipoToken.SALTO_LINEA, 3, 7), (TipoToken.APAGAR, 4, 1),
        (TipoToken.IDENTIFICADOR, 4, 8), (TipoToken.EOF, 4, 12),
    ]


def test_identificadores_distinguen_mayusculas() -> None:
    """Las palabras en minúsculas no son reservadas y las grafías se preservan."""
    tokens, errores = Lexer("encender LED1 led1").tokenizar()
    assert errores == []
    assert [(t.tipo, t.lexema, t.valor) for t in tokens[:-1]] == [
        (TipoToken.IDENTIFICADOR, "encender", "encender"),
        (TipoToken.IDENTIFICADOR, "LED1", "LED1"),
        (TipoToken.IDENTIFICADOR, "led1", "led1"),
    ]


def test_crlf_y_columnas() -> None:
    """CRLF genera un token y sitúa el siguiente carácter en la línea nueva."""
    tokens, errores = Lexer("A\r\n\tled1\r\n").tokenizar()
    assert errores == []
    assert tokens == [
        Token(TipoToken.A, "A", None, 1, 1),
        Token(TipoToken.SALTO_LINEA, "\r\n", None, 1, 2),
        Token(TipoToken.IDENTIFICADOR, "led1", "led1", 2, 2),
        Token(TipoToken.SALTO_LINEA, "\r\n", None, 2, 6),
        Token(TipoToken.EOF, "", None, 3, 1),
    ]


def test_entrada_vacia() -> None:
    """Una fuente vacía produce únicamente EOF."""
    assert Lexer("").tokenizar() == ([Token(TipoToken.EOF, "", None, 1, 1)], [])


def test_acumula_errores_en_lineas_distintas() -> None:
    """El análisis continúa después de caracteres no reconocidos."""
    tokens, errores = Lexer("ENCENDER led1@\nAPAGAR led1$").tokenizar()
    assert [(e.codigo, e.linea, e.columna) for e in errores] == [
        ("CARACTER_NO_RECONOCIDO", 1, 14),
        ("CARACTER_NO_RECONOCIDO", 2, 12),
    ]
    assert [t.tipo for t in tokens] == [
        TipoToken.ENCENDER, TipoToken.IDENTIFICADOR, TipoToken.SALTO_LINEA,
        TipoToken.APAGAR, TipoToken.IDENTIFICADOR, TipoToken.EOF,
    ]


def test_numero_seguido_de_identificador() -> None:
    """Las letras contiguas a un número inician un token independiente."""
    tokens, errores = Lexer("12abc 0 _x").tokenizar()
    assert errores == []
    assert [(t.tipo, t.valor, t.columna) for t in tokens] == [
        (TipoToken.NUMERO, 12, 1),
        (TipoToken.IDENTIFICADOR, "abc", 3),
        (TipoToken.NUMERO, 0, 7),
        (TipoToken.IDENTIFICADOR, "_x", 9),
        (TipoToken.EOF, None, 11),
    ]


def test_numero_superior_al_limite_de_conversion_de_python() -> None:
    """Los enteros largos se reconocen sin la excepción de int(string)."""
    texto = "1" + "0" * 4300
    tokens, errores = Lexer(texto).tokenizar()
    assert errores == []
    assert tokens[0].valor == 10 ** 4300
    assert tokens[-1].columna == 4302


def test_palabras_reservadas_y_no_reservadas() -> None:
    """Todas las palabras del lenguaje se reconocen sin reservar nombres de token."""
    palabras = (
        "ENCENDER APAGAR ACTIVAR DESACTIVAR CONSULTAR LISTAR DISPOSITIVOS "
        "NOTIFICAR ENVIAR CORREO A MENSAJE SI ENTONCES REPETIR VECES "
        "ENCENDIDO APAGADO ACTIVADA DESACTIVADA"
    )
    tokens, errores = Lexer(palabras + " IDENTIFICADOR CADENA NUMERO EOF").tokenizar()
    assert errores == []
    assert [token.tipo.value for token in tokens[:20]] == palabras.split()
    assert all(token.tipo == TipoToken.IDENTIFICADOR for token in tokens[20:-1])


def test_tokenizar_repetidamente() -> None:
    """Volver a analizar la fuente no acumula tokens ni diagnósticos anteriores."""
    lexer = Lexer("@\nA")
    primero = lexer.tokenizar()
    segundo = lexer.tokenizar()
    assert primero == segundo
