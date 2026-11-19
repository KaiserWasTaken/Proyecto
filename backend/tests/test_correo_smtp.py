"""Pruebas del adaptador SMTP y su integración opcional con Mailpit."""

import json
import os
import smtplib
import socket
from email.message import EmailMessage
from unittest.mock import MagicMock
from urllib.request import urlopen
from uuid import uuid4

import pytest

from app.services.correo_smtp import SmtpServicioCorreo
from app.vm.ports import ErrorCorreo


@pytest.fixture
def smtp_falso(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Sustituye SMTP y limpia la configuración heredada para las pruebas unitarias."""
    for variable in ("SMTP_HOST", "SMTP_PORT", "SMTP_FROM"):
        monkeypatch.delenv(variable, raising=False)
    fabrica = MagicMock()
    fabrica.return_value.__enter__.return_value.send_message.return_value = {}
    monkeypatch.setattr(smtplib, "SMTP", fabrica)
    return fabrica


def test_envia_cabeceras_y_cuerpo_utf8(smtp_falso: MagicMock) -> None:
    """El mensaje conserva las cabeceras y los caracteres de español."""
    SmtpServicioCorreo().enviar("a@b.com", "Información y señal")
    smtp_falso.assert_called_once_with("localhost", 1025, timeout=5)
    enviado: EmailMessage = smtp_falso.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert enviado["From"] == "commandflow@localhost"
    assert enviado["To"] == "a@b.com"
    assert enviado["Subject"] == "Mensaje de CommandFlow"
    assert enviado.get_content_charset() == "utf-8"
    assert enviado.get_content() == "Información y señal\n"


@pytest.mark.parametrize(
    "fallo",
    [ConnectionRefusedError("conexión rechazada"), TimeoutError("tiempo agotado")],
)
def test_errores_de_conexion_se_convierten(smtp_falso: MagicMock, fallo: OSError) -> None:
    """Conexiones rechazadas y timeouts producen ErrorCorreo con la causa."""
    smtp_falso.side_effect = fallo
    with pytest.raises(ErrorCorreo, match=str(fallo)):
        SmtpServicioCorreo().enviar("a@b.com", "Hola")


def test_destinatario_rechazado_se_convierte(smtp_falso: MagicMock) -> None:
    """Una respuesta SMTP de rechazo se informa mediante el puerto."""
    smtp_falso.return_value.__enter__.return_value.send_message.side_effect = (
        smtplib.SMTPRecipientsRefused({"a@b.com": (550, b"Rejected")})
    )
    with pytest.raises(ErrorCorreo, match="550"):
        SmtpServicioCorreo().enviar("a@b.com", "Hola")


def test_rechazo_devuelto_por_smtp_no_parece_exito(smtp_falso: MagicMock) -> None:
    """Un diccionario de destinatarios rechazados tampoco se ignora."""
    smtp_falso.return_value.__enter__.return_value.send_message.return_value = {
        "a@b.com": (550, b"Rejected")
    }
    with pytest.raises(ErrorCorreo, match="rechazó"):
        SmtpServicioCorreo().enviar("a@b.com", "Hola")


@pytest.mark.parametrize("destinatario", ["a@b.com\nBcc: otro@b.com", "a@b.com\rBcc: otro@b.com"])
def test_saltos_en_destinatario_se_rechazan_antes_de_conectar(
    smtp_falso: MagicMock, destinatario: str,
) -> None:
    """Una dirección con CR o LF no llega al servidor SMTP."""
    with pytest.raises(ErrorCorreo, match="saltos de línea"):
        SmtpServicioCorreo().enviar(destinatario, "Hola")
    smtp_falso.assert_not_called()


def test_configuracion_se_lee_al_construir(
    smtp_falso: MagicMock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Las variables se aplican al servicio creado, no al importar el módulo."""
    monkeypatch.setenv("SMTP_HOST", "smtp.local")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_FROM", "pruebas@example.com")
    servicio = SmtpServicioCorreo()
    monkeypatch.setenv("SMTP_HOST", "otro.local")
    servicio.enviar("a@b.com", "Hola")
    smtp_falso.assert_called_once_with("smtp.local", 2525, timeout=5)
    enviado: EmailMessage = smtp_falso.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert enviado["From"] == "pruebas@example.com"


def test_remitente_invalido_se_informa_sin_conectar(
    smtp_falso: MagicMock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un salto de línea en la cabecera From se comunica como ErrorCorreo."""
    monkeypatch.setenv("SMTP_FROM", "origen@ejemplo.com\nBcc: otro@ejemplo.com")
    with pytest.raises(ErrorCorreo, match="No se pudo enviar"):
        SmtpServicioCorreo().enviar("a@b.com", "Hola")
    smtp_falso.assert_not_called()


@pytest.mark.parametrize("puerto", ["texto", "0", "65536"])
def test_puerto_invalido_se_informa(
    smtp_falso: MagicMock, monkeypatch: pytest.MonkeyPatch, puerto: str,
) -> None:
    """Una configuración de puerto inválida no intenta conectarse."""
    monkeypatch.setenv("SMTP_PORT", puerto)
    with pytest.raises(ValueError, match="SMTP_PORT"):
        SmtpServicioCorreo()
    smtp_falso.assert_not_called()


@pytest.mark.mailpit
def test_correo_real_en_mailpit() -> None:
    """Envía un mensaje único y comprueba sus campos y cuerpo mediante la API."""
    host = os.environ.get("SMTP_HOST", "localhost")
    puerto = int(os.environ.get("SMTP_PORT", "1025"))
    try:
        with socket.create_connection((host, puerto), timeout=2):
            pass
    except OSError:
        pytest.skip("Mailpit no responde en SMTP_HOST:SMTP_PORT")

    mensaje = f"Prueba con acentos y ñ {uuid4().hex}"
    SmtpServicioCorreo().enviar("a@b.com", mensaje)
    with urlopen("http://localhost:8025/api/v1/messages", timeout=5) as respuesta:
        listado = json.load(respuesta)
    coincidencias = [entrada for entrada in listado["messages"] if mensaje in entrada["Snippet"]]
    assert len(coincidencias) == 1
    identificador = coincidencias[0]["ID"]
    with urlopen(f"http://localhost:8025/api/v1/message/{identificador}", timeout=5) as respuesta:
        recibido = json.load(respuesta)
    assert recibido["Subject"] == "Mensaje de CommandFlow"
    assert [destino["Address"] for destino in recibido["To"]] == ["a@b.com"]
    assert recibido["Text"].rstrip("\r\n") == mensaje
