"""Pruebas de los diagnósticos y el análisis sintáctico."""

from dataclasses import FrozenInstanceError

import pytest

from app.parser.errors import ErrorSintactico


def test_error_sintactico_es_inmutable_y_se_formatea() -> None:
    """El diagnóstico conserva su código, posición y mensaje sin permitir cambios."""
    error = ErrorSintactico("ESPERABA_IDENTIFICADOR", "Se esperaba un identificador", 2, 9)

    assert error.codigo == "ESPERABA_IDENTIFICADOR"
    assert str(error) == "Error sintáctico (línea 2, col 9): Se esperaba un identificador"
    with pytest.raises(FrozenInstanceError):
        setattr(error, "linea", 3)
