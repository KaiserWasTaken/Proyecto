"""Aplicación FastAPI de CommandFlow."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.engine import crear_engine, crear_fabrica_sesiones
from app.db.init_db import init_db
from app.services.correo_smtp import SmtpServicioCorreo


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicializa la base de datos y el servicio de correo al arrancar."""
    engine = crear_engine()
    try:
        init_db(engine)
        app.state.fabrica_sesiones = crear_fabrica_sesiones(engine)
        app.state.servicio_correo = SmtpServicioCorreo()
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
