"""Pruebas de los reintentos de inicialización de la aplicación."""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

import app.main as main


def test_arranque_reintenta_y_recupera(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un fallo temporal de conexión no impide inicializar la base."""
    intentos = 0
    esperas: list[float] = []
    engine = create_engine("sqlite://")

    def inicializar(_engine: object) -> None:
        nonlocal intentos
        intentos += 1
        if intentos < 3:
            raise OperationalError("conexión", {}, OSError("no disponible"))

    async def esperar(segundos: float) -> None:
        esperas.append(segundos)

    monkeypatch.setattr(main, "init_db", inicializar)
    monkeypatch.setattr(main.asyncio, "sleep", esperar)
    try:
        asyncio.run(main.inicializar_bd_con_reintentos(engine))
    finally:
        engine.dispose()
    assert intentos == 3
    assert esperas == [2, 2]


def test_arranque_agota_reintentos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un fallo persistente se propaga después de cinco intentos."""
    intentos = 0
    esperas: list[float] = []
    engine = create_engine("sqlite://")

    def inicializar(_engine: object) -> None:
        nonlocal intentos
        intentos += 1
        raise OperationalError("conexión", {}, OSError("no disponible"))

    async def esperar(segundos: float) -> None:
        esperas.append(segundos)

    monkeypatch.setattr(main, "init_db", inicializar)
    monkeypatch.setattr(main.asyncio, "sleep", esperar)
    try:
        with pytest.raises(OperationalError):
            asyncio.run(main.inicializar_bd_con_reintentos(engine))
    finally:
        engine.dispose()
    assert intentos == 5
    assert esperas == [2, 2, 2, 2]
