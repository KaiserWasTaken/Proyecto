"""Creación de tablas y carga inicial idempotente."""

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.models import Base, DispositivoDB
from app.db.repositorios import PostgresDispositivoRepository
from app.semantic.symbol_table import TablaSimbolos


def init_db(engine: Engine) -> None:
    """Crea las tablas y carga los dispositivos solo si la tabla está vacía."""
    Base.metadata.create_all(engine)
    with Session(engine) as sesion, sesion.begin():
        if sesion.scalar(select(DispositivoDB.identificador).limit(1)) is None:
            repositorio = PostgresDispositivoRepository(sesion)
            for simbolo in TablaSimbolos().listar():
                repositorio.registrar(simbolo)
