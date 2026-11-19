"""Pruebas HTTP de dispositivos y validación de comandos."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.routes import obtener_repositorio
from app.main import app
from app.semantic.symbol_table import DispositivoRepositoryMemoria, TablaSimbolos


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    """Proporciona un cliente con repositorio de prueba independiente."""
    repositorio = DispositivoRepositoryMemoria()
    for simbolo in TablaSimbolos().listar():
        repositorio.registrar(simbolo)
    app.dependency_overrides[obtener_repositorio] = lambda: repositorio
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.pop(obtener_repositorio, None)


def test_dispositivos(cliente: TestClient) -> None:
    """Devuelve los cuatro dispositivos con sus estados y operaciones."""
    respuesta = cliente.get("/api/devices")
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"identificador": "led1", "tipo": "LED", "estado": "APAGADO",
         "operaciones": ["APAGAR", "CONSULTAR", "ENCENDER"]},
        {"identificador": "led2", "tipo": "LED", "estado": "ENCENDIDO",
         "operaciones": ["APAGAR", "CONSULTAR", "ENCENDER"]},
        {"identificador": "alarma1", "tipo": "ALARMA", "estado": "ACTIVADA",
         "operaciones": ["ACTIVAR", "CONSULTAR", "DESACTIVAR"]},
        {"identificador": "ventilador1", "tipo": "VENTILADOR", "estado": "APAGADO",
         "operaciones": ["APAGAR", "CONSULTAR", "ENCENDER"]},
    ]


def test_comando_valido_no_modifica_estado(cliente: TestClient) -> None:
    """Validar devuelve la instrucción y no ejecuta el cambio de estado."""
    respuesta = cliente.post("/api/commands/validate", json={"source": "ENCENDER led1"})
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "valido": True,
        "errores": [],
        "instrucciones": [
            {"tipo": "CONTROL_DISPOSITIVO", "operacion": "ENCENDER", "dispositivo": "led1"}
        ],
    }
    dispositivos = cliente.get("/api/devices").json()
    assert next(d for d in dispositivos if d["identificador"] == "led1")["estado"] == "APAGADO"


@pytest.mark.parametrize(
    ("fuente", "fase", "codigo", "columna"),
    [
        ("ENCENDER led1@", "lexico", "CARACTER_NO_RECONOCIDO", 14),
        ("ENCENDER", "sintactico", "ESPERABA_IDENTIFICADOR", 9),
        ("ENCENDER dispositivo99", "semantico", "DISPOSITIVO_NO_EXISTE", 1),
        ("ENCENDER alarma1", "semantico", "OPERACION_INCOMPATIBLE", 1),
    ],
)
def test_errores_del_lenguaje(
    cliente: TestClient, fuente: str, fase: str, codigo: str, columna: int
) -> None:
    """Los errores del lenguaje se reportan con HTTP 200 y posición."""
    respuesta = cliente.post("/api/commands/validate", json={"source": fuente})
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["valido"] is False
    assert datos["instrucciones"] == []
    assert len(datos["errores"]) == 1
    error = datos["errores"][0]
    assert (error["fase"], error["codigo"], error["linea"], error["columna"]) == (
        fase, codigo, 1, columna
    )
    assert error["mensaje"]


def test_programa_mixto(cliente: TestClient) -> None:
    """Una línea válida y otra con error semántico aparecen en la respuesta."""
    respuesta = cliente.post(
        "/api/commands/validate", json={"source": "ENCENDER led1\nACTIVAR led1"}
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["valido"] is False
    assert datos["instrucciones"] == [
        {"tipo": "CONTROL_DISPOSITIVO", "operacion": "ENCENDER", "dispositivo": "led1"}
    ]
    assert [(e["fase"], e["codigo"], e["linea"]) for e in datos["errores"]] == [
        ("semantico", "OPERACION_INCOMPATIBLE", 2)
    ]


@pytest.mark.parametrize("body", [{}, {"source": 123}, {"source": None}])
def test_body_invalido(cliente: TestClient, body: dict[str, object]) -> None:
    """Pydantic rechaza una fuente ausente o de tipo incorrecto."""
    assert cliente.post("/api/commands/validate", json=body).status_code == 422


def test_cors_origen_de_desarrollo(cliente: TestClient) -> None:
    """El navegador puede hacer una petición previa desde el frontend local."""
    respuesta = cliente.options(
        "/api/commands/validate",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_repositorio_inicial_del_ciclo_de_vida() -> None:
    """Sin sustitución de dependencias, la app carga los dispositivos al iniciar."""
    with TestClient(app) as cliente:
        respuesta = cliente.get("/api/devices")
        assert respuesta.status_code == 200
        assert [d["identificador"] for d in respuesta.json()] == [
            "led1", "led2", "alarma1", "ventilador1"
        ]
