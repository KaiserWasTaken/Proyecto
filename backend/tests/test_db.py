"""Pruebas de persistencia, transacciones y contratos de base de datos."""

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.db.engine import crear_engine, crear_fabrica_sesiones
from app.db.init_db import init_db
from app.db.models import Base, EjecucionDB, NotificacionDB
from app.db.repositorios import (
    PostgresDispositivoRepository,
    PostgresRegistroNotificaciones,
    RepositorioEjecuciones,
)
from app.semantic.symbol_table import Simbolo


@pytest.fixture
def engine_sqlite() -> Iterator[Engine]:
    """Crea una base aislada en memoria para cada prueba."""
    engine = crear_engine("sqlite+pysqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture
def engine_postgres() -> Iterator[Engine]:
    """Usa PostgreSQL solo cuando DATABASE_URL lo selecciona explícitamente."""
    url = os.environ.get("DATABASE_URL")
    if not url or make_url(url).get_backend_name() != "postgresql":
        pytest.skip("DATABASE_URL no apunta a PostgreSQL")
    engine = crear_engine(url)
    yield engine
    engine.dispose()


def test_init_db_es_idempotente(engine_sqlite: Engine) -> None:
    """La segunda carga no duplica filas ni restablece estados."""
    init_db(engine_sqlite)
    fabrica = crear_fabrica_sesiones(engine_sqlite)
    with fabrica() as sesion:
        PostgresDispositivoRepository(sesion).actualizar_estado("led1", "ENCENDIDO")
        sesion.commit()
    init_db(engine_sqlite)
    with fabrica() as sesion:
        repositorio = PostgresDispositivoRepository(sesion)
        assert {s.identificador: s.estado for s in repositorio.listar()} == {
            "led1": "ENCENDIDO", "led2": "ENCENDIDO",
            "alarma1": "ACTIVADA", "ventilador1": "APAGADO",
        }


def test_init_db_no_rellena_tabla_parcial(engine_sqlite: Engine) -> None:
    """Una tabla no vacía se conserva aunque no tenga los cuatro dispositivos."""
    Base.metadata.create_all(engine_sqlite)
    with Session(engine_sqlite) as sesion:
        PostgresDispositivoRepository(sesion).registrar(Simbolo("otro", "LED", "ENCENDIDO"))
        sesion.commit()
    init_db(engine_sqlite)
    with Session(engine_sqlite) as sesion:
        assert PostgresDispositivoRepository(sesion).listar() == [Simbolo("otro", "LED", "ENCENDIDO")]


def test_commit_persiste_entre_sesiones(engine_sqlite: Engine) -> None:
    """Un estado confirmado se puede leer desde otra sesión."""
    init_db(engine_sqlite)
    fabrica = crear_fabrica_sesiones(engine_sqlite)
    with fabrica() as sesion:
        PostgresDispositivoRepository(sesion).actualizar_estado("led1", "ENCENDIDO")
        sesion.commit()
    with fabrica() as sesion:
        assert PostgresDispositivoRepository(sesion).obtener("led1") == Simbolo(
            "led1", "LED", "ENCENDIDO"
        )


def test_rollback_revierte_todos_los_repositorios(engine_sqlite: Engine) -> None:
    """Ningún repositorio confirma sus cambios sin decisión del llamador."""
    init_db(engine_sqlite)
    with Session(engine_sqlite) as sesion:
        dispositivos = PostgresDispositivoRepository(sesion)
        dispositivos.actualizar_estado("led1", "ENCENDIDO")
        dispositivos.registrar(Simbolo("temporal", "LED", "APAGADO"))
        PostgresRegistroNotificaciones(sesion).registrar("temporal")
        RepositorioEjecuciones(sesion).guardar("ENCENDER led1", True, [{"tipo": "SET_STATE"}])
        sesion.rollback()
    with Session(engine_sqlite) as sesion:
        dispositivos = PostgresDispositivoRepository(sesion)
        assert dispositivos.obtener("led1") == Simbolo("led1", "LED", "APAGADO")
        assert dispositivos.obtener("temporal") is None
        assert PostgresRegistroNotificaciones(sesion).listar() == []
        assert RepositorioEjecuciones(sesion).listar_ultimas(10) == []


def test_notificaciones_e_historial_se_guardan_en_orden(engine_sqlite: Engine) -> None:
    """La lectura posterior conserva orden, resultados y JSON anidado."""
    init_db(engine_sqlite)
    eventos: list[dict[str, object]] = [
        {"tipo": "GET_STATE", "dispositivo": "led1", "estado": "APAGADO"},
        {"tipo": "LIST_DEVICES", "dispositivos": [{"id": "led1", "estado": "APAGADO"}]},
    ]
    with Session(engine_sqlite) as sesion:
        notificaciones = PostgresRegistroNotificaciones(sesion)
        notificaciones.registrar("primera")
        notificaciones.registrar("segunda")
        historial = RepositorioEjecuciones(sesion)
        historial.guardar("CONSULTAR led1", True, eventos)
        historial.guardar("NOTIFICAR", False, [{"tipo": "ERROR", "texto": "fallo"}])
        sesion.commit()
    with Session(engine_sqlite) as sesion:
        assert [n.mensaje for n in PostgresRegistroNotificaciones(sesion).listar()] == [
            "primera", "segunda"
        ]
        historial = RepositorioEjecuciones(sesion)
        ultimas = historial.listar_ultimas(2)
        assert [(e.fuente, e.exito) for e in ultimas] == [
            ("NOTIFICAR", False), ("CONSULTAR led1", True)
        ]
        assert ultimas[1].eventos == eventos
        assert historial.listar_ultimas(1)[0].fuente == "NOTIFICAR"
        assert historial.listar_ultimas(0) == []
        with pytest.raises(ValueError):
            historial.listar_ultimas(-1)


def test_database_url_obligatoria(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin configuración de conexión se informa explícitamente el error."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        crear_engine()


@pytest.mark.postgres
def test_postgres_repositorio_y_rollback(engine_postgres: Engine) -> None:
    """La transacción PostgreSQL conserva el contrato y revierte la inserción."""
    identificador = f"test_{uuid4().hex}"
    with Session(engine_postgres) as sesion:
        repo = PostgresDispositivoRepository(sesion)
        repo.registrar(Simbolo(identificador, "LED", "APAGADO"))
        repo.actualizar_estado(identificador, "ENCENDIDO")
        assert repo.obtener(identificador) == Simbolo(identificador, "LED", "ENCENDIDO")
        sesion.rollback()
    with Session(engine_postgres) as sesion:
        assert PostgresDispositivoRepository(sesion).obtener(identificador) is None


@pytest.mark.postgres
def test_postgres_notificaciones_y_json_rollback(engine_postgres: Engine) -> None:
    """PostgreSQL guarda JSON y notificaciones sin confirmar la transacción."""
    clave = f"test_{uuid4().hex}"
    eventos: list[dict[str, object]] = [{"tipo": "NOTIFY", "texto": clave}]
    with Session(engine_postgres) as sesion:
        PostgresRegistroNotificaciones(sesion).registrar(clave)
        RepositorioEjecuciones(sesion).guardar(clave, True, eventos)
        ejecucion = sesion.scalar(select(EjecucionDB).where(EjecucionDB.fuente == clave))
        assert ejecucion is not None
        assert ejecucion.eventos == eventos
        assert sesion.scalar(select(NotificacionDB.id).where(NotificacionDB.mensaje == clave)) is not None
        sesion.rollback()
    with Session(engine_postgres) as sesion:
        assert sesion.scalar(select(EjecucionDB.id).where(EjecucionDB.fuente == clave)) is None
        assert sesion.scalar(select(NotificacionDB.id).where(NotificacionDB.mensaje == clave)) is None
