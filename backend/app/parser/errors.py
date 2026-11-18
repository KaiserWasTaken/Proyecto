"""Diagnósticos producidos durante el análisis sintáctico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorSintactico:
    """Error sintáctico con código y posición de base 1.

    Códigos: INSTRUCCION_DESCONOCIDA, ESPERABA_IDENTIFICADOR,
    ESPERABA_PALABRA, ESPERABA_CADENA, ESPERABA_NUMERO, ESPERABA_ESTADO,
    ESPERABA_OPERADOR, TOKENS_SOBRANTES y ANIDAMIENTO_NO_PERMITIDO.
    """

    codigo: str
    mensaje: str
    linea: int
    columna: int

    def __str__(self) -> str:
        """Presenta la posición y el mensaje de forma legible."""
        return f"Error sintáctico (línea {self.linea}, col {self.columna}): {self.mensaje}"
