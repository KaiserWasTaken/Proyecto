"""Aplicación FastAPI de CommandFlow."""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from app.api.routes import router
from app.db.engine import crear_engine, crear_fabrica_sesiones
from app.db.init_db import init_db
from app.services.correo_smtp import SmtpServicioCorreo

logger = logging.getLogger(__name__)


async def inicializar_bd_con_reintentos(engine: Engine) -> None:
    """Reintenta errores de conexión durante un periodo limitado al arrancar."""
    for intento in range(1, 6):
        try:
            init_db(engine)
            return
        except OperationalError:
            if intento == 5:
                raise
            logger.warning("Base de datos no disponible; reintento %d de 5", intento + 1)
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicializa la base de datos y el servicio de correo al arrancar."""
    engine = crear_engine()
    try:
        await inicializar_bd_con_reintentos(engine)
        app.state.fabrica_sesiones = crear_fabrica_sesiones(engine)
        app.state.servicio_correo = SmtpServicioCorreo()
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS", os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
