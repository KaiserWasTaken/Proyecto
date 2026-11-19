"""Integración de las fases léxica y sintáctica."""

from dataclasses import dataclass

from app.ast.nodes import Programa
from app.lexer.errors import ErrorLexico
from app.lexer.lexer import Lexer
from app.lexer.tokens import Token
from app.parser.errors import ErrorSintactico
from app.parser.parser import Parser


@dataclass(frozen=True)
class ResultadoAnalisis:
    """Resultado del análisis con diagnósticos separados por fase."""

    tokens: list[Token]
    errores_lexicos: list[ErrorLexico]
    programa: Programa
    errores_sintacticos: list[ErrorSintactico]

    @property
    def tiene_errores(self) -> bool:
        """Indica si cualquiera de las dos fases detectó errores."""
        return bool(self.errores_lexicos or self.errores_sintacticos)


def analizar(fuente: str) -> ResultadoAnalisis:
    """Analiza la fuente; si tiene_errores, no se pasa a semántica ni a ejecución."""
    tokens, errores_lexicos = Lexer(fuente).tokenizar()
    programa, errores_sintacticos = Parser(tokens).parsear()
    return ResultadoAnalisis(tokens, errores_lexicos, programa, errores_sintacticos)
