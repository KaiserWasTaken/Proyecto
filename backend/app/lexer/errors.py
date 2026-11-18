"""Errores producidos durante el análisis léxico."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorLexico:
    """Diagnóstico léxico con código y posición de base 1."""

    codigo: str
    mensaje: str
    linea: int
    columna: int

    def __str__(self) -> str:
        """Presenta la posición y el mensaje de forma legible."""
        return f"Error léxico (línea {self.linea}, col {self.columna}): {self.mensaje}"
