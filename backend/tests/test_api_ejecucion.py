"""Pruebas HTTP de ejecución y transacciones sin servicios externos."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.main as main
from app.api.routes import obtener_correo, obtener_sesion
from app.db.repositorios import PostgresRegistroNotificaciones, RepositorioEjecuciones
from app.ir.instructions import InstruccionIR, OpIR
from app.semantic.symbol_table import DispositivoRepository
from app.services import command_service
from app.vm.executor import ResultadoEjecucion
from app.vm.ports import RegistroNotificaciones, ServicioCorreo
from conftest import CorreoFalso


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


def test_encender_persiste_y_devuelve_evento(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """El estado confirmado es visible en una petición posterior."""
    cliente, _, _ = entorno
    resultado = ejecutar(cliente, "ENCENDER led1")
    assert resultado == {
        "valido": True, "exito": True, "errores": [],
        "eventos": [{"tipo": "SET_STATE", "texto": "led1 ahora ENCENDIDO",
                     "dispositivo": "led1", "estado": "ENCENDIDO"}],
    }
    assert estados(cliente)["led1"] == "ENCENDIDO"


@pytest.mark.parametrize(
    ("preparacion", "fuente", "dispositivo", "estado"),
    [
        ("ENCENDER led1", "APAGAR led1", "led1", "APAGADO"),
        ("DESACTIVAR alarma1", "ACTIVAR alarma1", "alarma1", "ACTIVADA"),
        ("ACTIVAR alarma1", "DESACTIVAR alarma1", "alarma1", "DESACTIVADA"),
    ],
)
def test_controles(
    entorno: tuple[TestClient, Engine, CorreoFalso], preparacion: str,
    fuente: str, dispositivo: str, estado: str,
) -> None:
    """Cada instrucción de control modifica el estado apropiado."""
    cliente, _, _ = entorno
    assert ejecutar(cliente, preparacion)["exito"] is True
    assert ejecutar(cliente, fuente)["exito"] is True
    assert estados(cliente)[dispositivo] == estado


def test_consultar_y_listar(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """La consulta no cambia estados y el listado incluye los cuatro dispositivos."""
    cliente, _, _ = entorno
    antes = estados(cliente)
    consulta = ejecutar(cliente, "CONSULTAR led1")
    assert consulta["eventos"] == [{
        "tipo": "GET_STATE", "texto": "led1 está APAGADO",
        "dispositivo": "led1", "estado": "APAGADO",
    }]
    listado = ejecutar(cliente, "LISTAR DISPOSITIVOS")
    eventos = listado["eventos"]
    assert isinstance(eventos, list)
    assert eventos[0]["tipo"] == "LIST_DEVICES"
    assert all(nombre in eventos[0]["texto"] for nombre in antes)
    assert estados(cliente) == antes


def test_notificacion_y_correo(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """La notificación se confirma en BD y el correo llega al puerto simulado."""
    cliente, engine, correo = entorno
    resultado = ejecutar(
        cliente, 'NOTIFICAR "Prueba"\nENVIAR CORREO A "a@b.com" MENSAJE "Hola"'
    )
    assert resultado["exito"] is True
    assert correo.enviados == [("a@b.com", "Hola")]
    eventos = resultado["eventos"]
    assert isinstance(eventos, list)
    assert [evento["tipo"] for evento in eventos] == ["NOTIFY", "SEND_EMAIL"]
    with Session(engine) as sesion:
        assert [n.mensaje for n in PostgresRegistroNotificaciones(sesion).listar()] == ["Prueba"]


@pytest.mark.parametrize("encendido", [True, False])
def test_condicional_led(
    entorno: tuple[TestClient, Engine, CorreoFalso], encendido: bool,
) -> None:
    """Solo una condición verdadera ejecuta el control anidado."""
    cliente, _, _ = entorno
    if encendido:
        ejecutar(cliente, "ENCENDER led1")
    resultado = ejecutar(cliente, "SI led1 == ENCENDIDO ENTONCES APAGAR led1")
    assert resultado["exito"] is True
    assert estados(cliente)["led1"] == "APAGADO"
    eventos = resultado["eventos"]
    assert isinstance(eventos, list)
    assert sum(e["tipo"] == "SET_STATE" for e in eventos) == int(encendido)


def test_condicional_notificacion(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """Una alarma activa registra y confirma su notificación."""
    cliente, engine, _ = entorno
    resultado = ejecutar(cliente, 'SI alarma1 == ACTIVADA ENTONCES NOTIFICAR "Alarma activada"')
    assert resultado["exito"] is True
    with Session(engine) as sesion:
        assert [n.mensaje for n in PostgresRegistroNotificaciones(sesion).listar()] == [
            "Alarma activada"
        ]


@pytest.mark.parametrize(
    ("fuente", "fase", "codigo"),
    [
        ("ENCENDER dispositivo99", "semantico", "DISPOSITIVO_NO_EXISTE"),
        ("ENCENDER alarma1", "semantico", "OPERACION_INCOMPATIBLE"),
        ("ENCENDER", "sintactico", "ESPERABA_IDENTIFICADOR"),
        ("ENCENDER led1@", "lexico", "CARACTER_NO_RECONOCIDO"),
    ],
)
def test_errores_impiden_ejecucion(
    entorno: tuple[TestClient, Engine, CorreoFalso], fuente: str, fase: str, codigo: str,
) -> None:
    """Los errores del lenguaje no modifican el estado y quedan en el historial."""
    cliente, engine, _ = entorno
    antes = estados(cliente)
    resultado = ejecutar(cliente, fuente)
    assert resultado["valido"] is False
    assert resultado["exito"] is False
    assert resultado["eventos"] == []
    errores = resultado["errores"]
    assert isinstance(errores, list)
    assert errores[0]["fase"] == fase and errores[0]["codigo"] == codigo
    assert estados(cliente) == antes
    with Session(engine) as sesion:
        historial = RepositorioEjecuciones(sesion).listar_ultimas(1)
        assert len(historial) == 1 and historial[0].fuente == fuente and not historial[0].exito


def test_error_semantico_en_medio_no_ejecuta_nada(
    entorno: tuple[TestClient, Engine, CorreoFalso],
) -> None:
    """Ninguna de las líneas válidas de un programa inválido se ejecuta."""
    cliente, _, _ = entorno
    assert ejecutar(cliente, "APAGAR led2")["exito"] is True
    antes = estados(cliente)
    resultado = ejecutar(cliente, "ENCENDER led1\nENCENDER dispositivo99\nENCENDER led2")
    assert resultado["valido"] is False and resultado["eventos"] == []
    errores = resultado["errores"]
    assert isinstance(errores, list)
    assert errores[0]["linea"] == 2
    assert estados(cliente) == antes


def test_fallo_correo_confirma_instrucciones_restantes(
    entorno: tuple[TestClient, Engine, CorreoFalso],
) -> None:
    """El fallo de correo no aborta ni revierte los cambios posteriores."""
    cliente, engine, correo = entorno
    correo.fallar = True
    resultado = ejecutar(
        cliente,
        'ENVIAR CORREO A "a@b.com" MENSAJE "Hola"\nENCENDER led1\nNOTIFICAR "después"',
    )
    assert resultado["valido"] is True and resultado["exito"] is False
    eventos = resultado["eventos"]
    assert isinstance(eventos, list)
    assert [e["tipo"] for e in eventos] == ["ERROR_CORREO", "SET_STATE", "NOTIFY"]
    assert estados(cliente)["led1"] == "ENCENDIDO"
    with Session(engine) as sesion:
        assert [n.mensaje for n in PostgresRegistroNotificaciones(sesion).listar()] == ["después"]
        assert RepositorioEjecuciones(sesion).listar_ultimas(1)[0].exito is False


@pytest.mark.parametrize("fallo", ["dispositivo", "limite"])
def test_aborto_revierte_cambios_y_guarda_historial(
    entorno: tuple[TestClient, Engine, CorreoFalso], monkeypatch: pytest.MonkeyPatch, fallo: str,
) -> None:
    """Un error interno o límite revierte estado y notificación, pero se registra."""
    cliente, engine, _ = entorno

    def ir_invalido(_instrucciones: list[dict[str, object]]) -> list[InstruccionIR]:
        """Fuerza un error tras dos acciones que ya hicieron flush."""
        prefijo = [
            InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
            InstruccionIR(OpIR.NOTIFY, ("temporal",)),
        ]
        if fallo == "limite":
            return prefijo + [
                InstruccionIR(OpIR.COMPARE, ("led1", "==", "APAGADO")),
                InstruccionIR(OpIR.JUMP_IF_FALSE, (3,)),
                InstruccionIR(OpIR.HALT),
            ]
        return prefijo + [
            InstruccionIR(OpIR.SET_STATE, ("inexistente", "ENCENDIDO")),
            InstruccionIR(OpIR.HALT),
        ]

    monkeypatch.setattr(command_service, "generar_ir", ir_invalido)
    resultado = ejecutar(cliente, "ENCENDER led1")
    assert resultado["valido"] is True and resultado["exito"] is False
    eventos = resultado["eventos"]
    assert isinstance(eventos, list)
    assert eventos[-1]["tipo"] == "ERROR_EJECUCION"
    assert "revirtieron" in eventos[-1]["texto"]
    if fallo == "limite":
        assert any("límite" in evento["texto"] for evento in eventos)
    assert estados(cliente)["led1"] == "APAGADO"
    with Session(engine) as sesion:
        assert PostgresRegistroNotificaciones(sesion).listar() == []
        historial = RepositorioEjecuciones(sesion).listar_ultimas(1)
        assert len(historial) == 1 and historial[0].exito is False
        assert historial[0].eventos == eventos


def test_excepcion_inesperada_revierte_y_registra(
    entorno: tuple[TestClient, Engine, CorreoFalso], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Una excepción inesperada durante la ejecución no deja cambios parciales."""
    cliente, engine, _ = entorno

    class EjecutorFallido:
        """Simula un ejecutor que falla después de dos escrituras."""

        def __init__(
            self, repositorio: DispositivoRepository, correo: ServicioCorreo,
            notificaciones: RegistroNotificaciones,
        ) -> None:
            """Retiene los puertos para simular los efectos previos al fallo."""
            self.repositorio = repositorio
            self.notificaciones = notificaciones

        def ejecutar(self, _ir: list[InstruccionIR]) -> ResultadoEjecucion:
            """Escribe en la sesión y lanza un error inesperado."""
            self.repositorio.actualizar_estado("led1", "ENCENDIDO")
            self.notificaciones.registrar("temporal")
            raise RuntimeError("fallo simulado")

    monkeypatch.setattr(command_service, "Ejecutor", EjecutorFallido)
    resultado = ejecutar(cliente, "ENCENDER led1")
    assert resultado["valido"] is True and resultado["exito"] is False
    assert estados(cliente)["led1"] == "APAGADO"
    with Session(engine) as sesion:
        assert PostgresRegistroNotificaciones(sesion).listar() == []
        assert RepositorioEjecuciones(sesion).listar_ultimas(1)[0].exito is False


def test_redundante_y_validate_sin_historial(
    entorno: tuple[TestClient, Engine, CorreoFalso],
) -> None:
    """Validar no escribe; dos controles repetidos se ejecutan optimizados."""
    cliente, engine, _ = entorno
    assert cliente.post("/api/commands/validate", json={"source": "ENCENDER led1"}).json()["valido"]
    assert estados(cliente)["led1"] == "APAGADO"
    with Session(engine) as sesion:
        assert RepositorioEjecuciones(sesion).listar_ultimas(10) == []
    resultado = ejecutar(cliente, "ENCENDER led1\nENCENDER led1")
    assert resultado["exito"] is True and estados(cliente)["led1"] == "ENCENDIDO"
    eventos = resultado["eventos"]
    assert isinstance(eventos, list)
    assert [e["tipo"] for e in eventos] == ["SET_STATE"]


def test_historial_registra_exito_y_error(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """Los intentos válidos e inválidos se guardan con su resultado correcto."""
    cliente, engine, _ = entorno
    ejecutar(cliente, "ENCENDER led1")
    ejecutar(cliente, "ENCENDER dispositivo99")
    with Session(engine) as sesion:
        filas = RepositorioEjecuciones(sesion).listar_ultimas(2)
        assert [(fila.fuente, fila.exito) for fila in filas] == [
            ("ENCENDER dispositivo99", False), ("ENCENDER led1", True)
        ]
