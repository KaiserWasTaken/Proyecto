"""Adaptador SMTP del puerto de correo."""

import os
import smtplib
from email.message import EmailMessage

from app.vm.ports import ErrorCorreo, ServicioCorreo


class SmtpServicioCorreo(ServicioCorreo):
    """Envía mensajes a un servidor SMTP sin autenticación ni TLS."""

    def __init__(self) -> None:
        """Lee la configuración del entorno al construir el servicio."""
        self._host = os.environ.get("SMTP_HOST", "localhost")
        puerto = os.environ.get("SMTP_PORT", "1025")
        try:
            self._puerto = int(puerto)
        except ValueError as error:
            raise ValueError("SMTP_PORT debe ser un puerto numérico entre 1 y 65535") from error
        if not 1 <= self._puerto <= 65535:
            raise ValueError("SMTP_PORT debe ser un puerto numérico entre 1 y 65535")
        self._remitente = os.environ.get("SMTP_FROM", "commandflow@localhost")

    def enviar(self, destinatario: str, mensaje: str) -> None:
        """Envía un mensaje UTF-8 o convierte el fallo de SMTP en ErrorCorreo."""
        if "\r" in destinatario or "\n" in destinatario:
            raise ErrorCorreo("El destinatario no puede contener saltos de línea")
        try:
            correo = EmailMessage()
            correo["From"] = self._remitente
            correo["To"] = destinatario
            correo["Subject"] = "Mensaje de CommandFlow"
            correo.set_content(mensaje, charset="utf-8")
            with smtplib.SMTP(self._host, self._puerto, timeout=5) as conexion:
                rechazados = conexion.send_message(correo)
                if rechazados:
                    raise ErrorCorreo("El servidor SMTP rechazó el destinatario")
        except (OSError, smtplib.SMTPException, ValueError) as error:
            raise ErrorCorreo(f"No se pudo enviar el correo: {error}") from error
