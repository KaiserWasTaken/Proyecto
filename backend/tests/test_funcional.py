"""Escenarios funcionales de la sección 16 contra la API de ejecución."""

import json
import os
import socket
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

import app.main as main
from app.api.routes import obtener_correo
from app.db.repositorios import PostgresRegistroNotificaciones, RepositorioEjecuciones
from app.optimizer.optimizer import optimizar
from app.services.correo_smtp import SmtpServicioCorreo
from conftest import (
    CorreoFalso, compilar, comprobar_equivalencia, ejecutar, estados, repositorio_inicial,
)


def test_encender_led1(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ENCENDER led1 deja led1 ENCENDIDO."""
    cliente, _, _ = entorno
    assert ejecutar(cliente, "ENCENDER led1")["exito"] is True
    assert estados(cliente)["led1"] == "ENCENDIDO"


def test_apagar_led1(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """APAGAR led1 deja led1 APAGADO."""
    cliente, _, _ = entorno
    assert ejecutar(cliente, "ENCENDER led1")["exito"] is True
    assert ejecutar(cliente, "APAGAR led1")["exito"] is True
    assert estados(cliente)["led1"] == "APAGADO"


def test_activar_alarma1(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ACTIVAR alarma1 deja la alarma ACTIVADA."""
    cliente, _, _ = entorno
    assert ejecutar(cliente, "DESACTIVAR alarma1")["exito"] is True
    assert ejecutar(cliente, "ACTIVAR alarma1")["exito"] is True
    assert estados(cliente)["alarma1"] == "ACTIVADA"


def test_desactivar_alarma1(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """DESACTIVAR alarma1 deja la alarma DESACTIVADA."""
    cliente, _, _ = entorno
    assert estados(cliente)["alarma1"] == "ACTIVADA"
    assert ejecutar(cliente, "DESACTIVAR alarma1")["exito"] is True
    assert estados(cliente)["alarma1"] == "DESACTIVADA"


def test_consultar_led1(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """CONSULTAR led1 devuelve su estado actual."""
    cliente, _, _ = entorno
    resultado = ejecutar(cliente, "CONSULTAR led1")
    assert resultado["exito"] is True
    assert resultado["eventos"] == [{
        "tipo": "GET_STATE", "texto": "led1 está APAGADO",
        "dispositivo": "led1", "estado": "APAGADO",
    }]


def test_listar_dispositivos(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """LISTAR DISPOSITIVOS produce un evento con los cuatro dispositivos."""
    cliente, _, _ = entorno
    resultado = ejecutar(cliente, "LISTAR DISPOSITIVOS")
    assert resultado["exito"] is True
    eventos = resultado["eventos"]
    assert isinstance(eventos, list) and len(eventos) == 1
    assert eventos[0]["tipo"] == "LIST_DEVICES"
    for texto in ("led1 LED APAGADO", "led2 LED ENCENDIDO",
                  "alarma1 ALARMA ACTIVADA", "ventilador1 VENTILADOR APAGADO"):
        assert texto in eventos[0]["texto"]


def test_encender_dispositivo_inexistente(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ENCENDER dispositivo99 produce DISPOSITIVO_NO_EXISTE."""
    cliente, _, _ = entorno
    resultado = ejecutar(cliente, "ENCENDER dispositivo99")
    assert resultado["valido"] is False
    errores = resultado["errores"]
    assert isinstance(errores, list)
    assert [(error["fase"], error["codigo"]) for error in errores] == [
        ("semantico", "DISPOSITIVO_NO_EXISTE")
    ]


def test_encender_alarma_incompatible(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ENCENDER alarma1 produce OPERACION_INCOMPATIBLE."""
    cliente, _, _ = entorno
    resultado = ejecutar(cliente, "ENCENDER alarma1")
    assert resultado["valido"] is False
    errores = resultado["errores"]
    assert isinstance(errores, list)
    assert [(error["fase"], error["codigo"]) for error in errores] == [
        ("semantico", "OPERACION_INCOMPATIBLE")
    ]


def test_encender_sin_identificador(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ENCENDER sin identificador produce un error sintáctico."""
    cliente, _, _ = entorno
    resultado = ejecutar(cliente, "ENCENDER")
    assert resultado["valido"] is False
    errores = resultado["errores"]
    assert isinstance(errores, list) and errores[0]["fase"] == "sintactico"


def test_encender_con_caracter_invalido(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ENCENDER led1@ produce un error léxico."""
    cliente, _, _ = entorno
    resultado = ejecutar(cliente, "ENCENDER led1@")
    assert resultado["valido"] is False
    errores = resultado["errores"]
    assert isinstance(errores, list) and errores[0]["fase"] == "lexico"


def test_notificar_prueba(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """NOTIFICAR \"Prueba\" registra el evento y la notificación en BD."""
    cliente, engine, _ = entorno
    resultado = ejecutar(cliente, 'NOTIFICAR "Prueba"')
    assert resultado["exito"] is True
    assert resultado["eventos"] == [{"tipo": "NOTIFY", "texto": "Notificación registrada: Prueba"}]
    with Session(engine) as sesion:
        assert [n.mensaje for n in PostgresRegistroNotificaciones(sesion).listar()] == ["Prueba"]


def test_enviar_correo(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ENVIAR CORREO A \"a@b.com\" MENSAJE \"Hola\" llega al servicio simulado."""
    cliente, _, correo = entorno
    resultado = ejecutar(cliente, 'ENVIAR CORREO A "a@b.com" MENSAJE "Hola"')
    assert resultado["exito"] is True
    assert correo.enviados == [("a@b.com", "Hola")]
    assert resultado["eventos"] == [{"tipo": "SEND_EMAIL", "texto": "Correo enviado a a@b.com"}]


@pytest.mark.parametrize("encendido", [True, False], ids=["se_cumple", "no_se_cumple"])
def test_si_led_encendido_apagar(
    entorno: tuple[TestClient, Engine, CorreoFalso], encendido: bool,
) -> None:
    """SI led1 == ENCENDIDO ENTONCES APAGAR led1 respeta la condición."""
    cliente, _, _ = entorno
    if encendido:
        assert ejecutar(cliente, "ENCENDER led1")["exito"] is True
    resultado = ejecutar(cliente, "SI led1 == ENCENDIDO ENTONCES APAGAR led1")
    assert resultado["exito"] is True
    assert estados(cliente)["led1"] == "APAGADO"
    eventos = resultado["eventos"]
    assert isinstance(eventos, list)
    assert sum(evento["tipo"] == "SET_STATE" for evento in eventos) == int(encendido)


def test_programa_invalido_no_ejecuta_nada(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ENCENDER led1 seguido de un dispositivo inexistente no cambia led1."""
    cliente, _, _ = entorno
    antes = estados(cliente)
    resultado = ejecutar(cliente, "ENCENDER led1\nENCENDER dispositivo99")
    assert resultado["valido"] is False and resultado["eventos"] == []
    assert estados(cliente) == antes


def test_optimizaciones_conservan_resultados() -> None:
    """Compara con y sin optimización un programa con asignaciones redundantes."""
    fuente = "ENCENDER led1\nENCENDER led1\nAPAGAR led1"
    assert optimizar(compilar(fuente, repositorio_inicial())).cambios
    comprobar_equivalencia(fuente)


def test_fallo_correo_continua(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """El fallo de correo produce exito=false y continúa los eventos posteriores."""
    cliente, _, correo = entorno
    correo.fallar = True
    resultado = ejecutar(
        cliente, 'ENVIAR CORREO A "a@b.com" MENSAJE "Hola"\nENCENDER led1\nNOTIFICAR "Prueba"'
    )
    assert resultado["valido"] is True and resultado["exito"] is False
    eventos = resultado["eventos"]
    assert isinstance(eventos, list)
    assert [evento["tipo"] for evento in eventos] == ["ERROR_CORREO", "SET_STATE", "NOTIFY"]
    assert estados(cliente)["led1"] == "ENCENDIDO"


def test_validate_sin_commit_ni_cambios(
    entorno: tuple[TestClient, Engine, CorreoFalso], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST validate no confirma la sesión, cambia estados ni escribe historial."""
    cliente, engine, _ = entorno
    commits: list[str] = []
    commit_original = Session.commit

    def registrar_commit(sesion: Session) -> None:
        """Registra cualquier intento de commit de la sesión."""
        commits.append("sesión")
        commit_original(sesion)

    def registrar_commit_motor(_conexion: Connection) -> None:
        """Registra commits de transacciones a nivel de conexión."""
        commits.append("conexión")

    monkeypatch.setattr(Session, "commit", registrar_commit)
    event.listen(engine, "commit", registrar_commit_motor)
    try:
        antes = estados(cliente)
        respuesta = cliente.post("/api/commands/validate", json={"source": "ENCENDER led1"})
        assert respuesta.status_code == 200 and respuesta.json()["valido"] is True
        assert estados(cliente) == antes
        with Session(engine) as sesion:
            assert RepositorioEjecuciones(sesion).listar_ultimas(10) == []
    finally:
        event.remove(engine, "commit", registrar_commit_motor)
    assert commits == []


@pytest.mark.mailpit
def test_enviar_correo_real_desde_endpoint(entorno: tuple[TestClient, Engine, CorreoFalso]) -> None:
    """ENVIAR CORREO desde execute aparece realmente en la API de Mailpit."""
    cliente, _, correo_falso = entorno
    host = os.environ.get("SMTP_HOST", "localhost")
    puerto = int(os.environ.get("SMTP_PORT", "1025"))
    try:
        with socket.create_connection((host, puerto), timeout=2):
            pass
    except OSError:
        pytest.skip("Mailpit no responde en SMTP_HOST:SMTP_PORT")

    with urlopen("http://localhost:8025/api/v1/messages", timeout=5) as respuesta:
        anteriores = {entrada["ID"] for entrada in json.load(respuesta)["messages"]}

    main.app.dependency_overrides[obtener_correo] = lambda: SmtpServicioCorreo()
    try:
        resultado = ejecutar(cliente, 'ENVIAR CORREO A "a@b.com" MENSAJE "Hola"')
    finally:
        main.app.dependency_overrides[obtener_correo] = lambda: correo_falso
    assert resultado["valido"] is True and resultado["exito"] is True

    with urlopen("http://localhost:8025/api/v1/messages", timeout=5) as respuesta:
        nuevos = [entrada for entrada in json.load(respuesta)["messages"] if entrada["ID"] not in anteriores]
    coincidencias = [
        entrada for entrada in nuevos
        if entrada["Subject"] == "Mensaje de CommandFlow"
        and any(destino["Address"] == "a@b.com" for destino in entrada["To"])
    ]
    assert len(coincidencias) == 1
    with urlopen(f'http://localhost:8025/api/v1/message/{coincidencias[0]["ID"]}', timeout=5) as respuesta:
        recibido = json.load(respuesta)
    assert recibido["Text"].rstrip("\r\n") == "Hola"
