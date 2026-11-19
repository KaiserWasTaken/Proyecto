"""Colaboradores en memoria para probar la ejecución del IR."""

from app.ir.generator import generar_ir
from app.ir.instructions import InstruccionIR
from app.semantic.analyzer import Analizador
from app.semantic.symbol_table import DispositivoRepositoryMemoria, TablaSimbolos
from app.services.frontend_pipeline import analizar
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
