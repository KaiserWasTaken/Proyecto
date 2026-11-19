"""Colaboradores compartidos para probar la ejecución del IR y la API."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.main as main
from app.api.routes import obtener_correo, obtener_sesion
from app.ir.generator import generar_ir
from app.ir.instructions import InstruccionIR, OpIR
from app.optimizer.optimizer import optimizar
from app.semantic.analyzer import Analizador
from app.semantic.symbol_table import DispositivoRepositoryMemoria, TablaSimbolos
from app.services.frontend_pipeline import analizar
from app.vm.executor import Ejecutor
from app.vm.ports import ErrorCorreo, RegistroNotificaciones, ServicioCorreo


class CorreoFalso(ServicioCorreo):
    """Conserva los correos enviados o simula un fallo explícito."""

    def __init__(self, fallar: bool = False) -> None:
        """Configura si el envío debe fallar."""
        self.enviados: list[tuple[str, str]] = []
        self.fallar = fallar

    def enviar(self, destinatario: str, mensaje: str) -> None:
        """Guarda el correo o informa del fallo simulado."""
        if self.fallar:
            raise ErrorCorreo("servicio no disponible")
        self.enviados.append((destinatario, mensaje))


class NotificacionesFalsas(RegistroNotificaciones):
    """Conserva las notificaciones registradas en memoria."""

    def __init__(self) -> None:
        """Inicializa la lista de mensajes."""
        self.mensajes: list[str] = []

    def registrar(self, mensaje: str) -> None:
        """Guarda el mensaje recibido."""
        self.mensajes.append(mensaje)


def repositorio_inicial() -> DispositivoRepositoryMemoria:
    """Crea un repositorio independiente con los dispositivos iniciales."""
    repositorio = DispositivoRepositoryMemoria()
    for simbolo in TablaSimbolos().listar():
        repositorio.registrar(simbolo)
    return repositorio


def compilar(fuente: str, repositorio: DispositivoRepositoryMemoria) -> list[InstruccionIR]:
    """Aplica el pipeline completo a un programa que debe ser válido."""
    analisis = analizar(fuente)
    assert not analisis.tiene_errores, f"Fuente inválida:\n{fuente}\n{analisis}"
    instrucciones, errores = Analizador(repositorio).analizar(analisis.programa)
    assert not errores, f"Errores semánticos en:\n{fuente}\n{errores}"
    return generar_ir(instrucciones)


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, Engine, CorreoFalso]]:
    """Proporciona una aplicación aislada con sesión y correo sustituibles."""
    # TestClient usa otros hilos: StaticPool comparte la misma SQLite en memoria.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    correo = CorreoFalso()
    monkeypatch.setattr(main, "crear_engine", lambda: engine)

    def sesion_prueba() -> Iterator[Session]:
        """Cede una sesión para cada petición HTTP."""
        with Session(engine) as sesion:
            yield sesion

    main.app.dependency_overrides[obtener_sesion] = sesion_prueba
    main.app.dependency_overrides[obtener_correo] = lambda: correo
    try:
        with TestClient(main.app) as cliente:
            yield cliente, engine, correo
    finally:
        main.app.dependency_overrides.pop(obtener_sesion, None)
        main.app.dependency_overrides.pop(obtener_correo, None)


def estados(cliente: TestClient) -> dict[str, str]:
    """Consulta los estados actuales desde el endpoint público."""
    respuesta = cliente.get("/api/devices")
    assert respuesta.status_code == 200
    return {d["identificador"]: d["estado"] for d in respuesta.json()}


def ejecutar(cliente: TestClient, fuente: str) -> dict[str, object]:
    """Envía un programa y exige la respuesta HTTP normal."""
    respuesta = cliente.post("/api/commands/execute", json={"source": fuente})
    assert respuesta.status_code == 200
    return respuesta.json()


def comprobar_equivalencia(fuente: str) -> None:
    """Compara efectos visibles y estados al ejecutar una fuente con y sin optimización."""
    repositorios = [repositorio_inicial(), repositorio_inicial()]
    ir = compilar(fuente, repositorios[0])
    variantes = [ir, optimizar(ir).ir_optimizado]
    resultados = []
    for repositorio, instrucciones in zip(repositorios, variantes, strict=True):
        correo, notificaciones = CorreoFalso(), NotificacionesFalsas()
        resultado = Ejecutor(repositorio, correo, notificaciones).ejecutar(instrucciones)
        assert resultado.exito, f"Error al ejecutar:\n{fuente}\n{resultado.errores}"
        resultados.append((
            repositorio.listar(),
            [evento for evento in resultado.eventos if evento.tipo != OpIR.SET_STATE.value],
            correo.enviados,
            notificaciones.mensajes,
        ))
    assert resultados[0] == resultados[1], f"Diferencia para el programa:\n{fuente}"
