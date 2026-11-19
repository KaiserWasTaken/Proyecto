"""Puertos de salida utilizados por el ejecutor."""

from abc import ABC, abstractmethod


class ErrorCorreo(Exception):
    """Fallo esperado al enviar un correo."""


class ServicioCorreo(ABC):
    """Puerto para el envío de correos."""

    @abstractmethod
    def enviar(self, destinatario: str, mensaje: str) -> None:
        """Envía el mensaje o lanza ErrorCorreo si falla."""


class RegistroNotificaciones(ABC):
    """Puerto para registrar notificaciones."""

    @abstractmethod
    def registrar(self, mensaje: str) -> None:
        """Registra una notificación."""
