"""Pruebas del servicio sin utilizar FastAPI."""

import pytest

from app.semantic.symbol_table import DispositivoRepositoryMemoria
from app.services import command_service


@pytest.mark.parametrize(
    ("fuente", "esperados"),
    [
        ("ENCENDER led1@", [("lexico", "CARACTER_NO_RECONOCIDO")]),
        ("ENCENDER", [("sintactico", "ESPERABA_IDENTIFICADOR")]),
        ("ENCENDER led1@\nENCENDER", [
            ("lexico", "CARACTER_NO_RECONOCIDO"),
            ("sintactico", "ESPERABA_IDENTIFICADOR"),
        ]),
    ],
)
def test_errores_previos_bloquean_semantica(
    monkeypatch: pytest.MonkeyPatch, fuente: str, esperados: list[tuple[str, str]]
) -> None:
    """Los errores del lexer o parser impiden incluso crear el analizador."""
    def analizador_prohibido(*args: object, **kwargs: object) -> None:
        """Falla si se intenta ejecutar la fase semántica."""
        raise AssertionError("No debe ejecutarse el analizador semántico")

    monkeypatch.setattr(command_service, "Analizador", analizador_prohibido)
    resultado = command_service.validar_comandos(fuente, DispositivoRepositoryMemoria())
    assert resultado["valido"] is False
    assert resultado["instrucciones"] == []
    assert [(e["fase"], e["codigo"]) for e in resultado["errores"]] == esperados
