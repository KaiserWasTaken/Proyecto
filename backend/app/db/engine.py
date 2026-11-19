"""Creación del motor y de sesiones sin depender de la API."""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker


def crear_engine(database_url: str | None = None) -> Engine:
    """Crea un motor desde la URL proporcionada o DATABASE_URL."""
    url = database_url if database_url is not None else os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL no está configurada")
    parsed = make_url(url)
    if parsed.drivername == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
    return create_engine(parsed)


def crear_fabrica_sesiones(engine: Engine) -> sessionmaker[Session]:
    """Crea una fábrica de sesiones asociada al motor."""
    return sessionmaker(bind=engine)
