"""Aplicación FastAPI de CommandFlow."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.semantic.symbol_table import DispositivoRepositoryMemoria, TablaSimbolos


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicializa una instancia compartida del repositorio al arrancar."""
    repositorio = DispositivoRepositoryMemoria()
    for simbolo in TablaSimbolos().listar():
        repositorio.registrar(simbolo)
    app.state.repositorio = repositorio
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
