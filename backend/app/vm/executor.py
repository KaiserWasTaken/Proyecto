"""Máquina virtual iterativa para las instrucciones intermedias.

Un fallo de correo se registra y la ejecución continúa: las acciones posteriores
son independientes del envío fallido. El resultado señala el fallo con exito=False.
"""

from dataclasses import dataclass

from app.ir.instructions import InstruccionIR, OpIR
from app.semantic.symbol_table import (
    DispositivoRepository,
    ErrorTablaSimbolos,
    Simbolo,
    TablaSimbolos,
)
from app.vm.ports import ErrorCorreo, RegistroNotificaciones, ServicioCorreo


MAXIMO_INSTRUCCIONES = 10_000


@dataclass(frozen=True)
class EventoEjecucion:
    """Resultado de una instrucción o de un error de ejecución."""

    tipo: str
    texto: str
    dispositivo: str | None = None
    estado: str | None = None
    dispositivos: tuple[Simbolo, ...] | None = None


@dataclass(frozen=True)
class ResultadoEjecucion:
    """Eventos ordenados y errores detectados durante la ejecución."""

    eventos: list[EventoEjecucion]
    exito: bool
    errores: list[str]


class ErrorIR(ValueError):
    """Instrucción intermedia inválida para el ejecutor."""


def _textos(instruccion: InstruccionIR, cantidad: int) -> tuple[str, ...]:
    """Valida la cantidad y el tipo de argumentos textuales."""
    if len(instruccion.args) != cantidad or not all(
        isinstance(arg, str) for arg in instruccion.args
    ):
        raise ErrorIR(f"Argumentos inválidos para {instruccion.op}")
    return tuple(arg for arg in instruccion.args if isinstance(arg, str))


class Ejecutor:
    """Ejecuta IR sobre dispositivos y puertos proporcionados por el llamador."""

    def __init__(
        self,
        repositorio: DispositivoRepository,
        servicio_correo: ServicioCorreo,
        registro_notificaciones: RegistroNotificaciones,
    ) -> None:
        """Usa el repositorio y los puertos inyectados sin crear infraestructura."""
        self._tabla = TablaSimbolos(repositorio)
        self._correo = servicio_correo
        self._notificaciones = registro_notificaciones

    def ejecutar(self, ir: list[InstruccionIR]) -> ResultadoEjecucion:
        """Ejecuta hasta HALT o un error fatal; los errores de correo no interrumpen."""
        eventos: list[EventoEjecucion] = []
        errores: list[str] = []
        posicion = 0
        ejecutadas = 0
        comparacion: bool | None = None

        try:
            while True:
                if ejecutadas >= MAXIMO_INSTRUCCIONES:
                    raise ErrorIR(f"Se alcanzó el límite de {MAXIMO_INSTRUCCIONES} instrucciones")
                if not 0 <= posicion < len(ir):
                    raise ErrorIR(f"Puntero de instrucción fuera del IR: {posicion}")
                instruccion = ir[posicion]
                ejecutadas += 1
                posicion += 1

                if instruccion.op == OpIR.HALT:
                    _textos(instruccion, 0)
                    break
                if instruccion.op == OpIR.SET_STATE:
                    dispositivo, estado = _textos(instruccion, 2)
                    self._tabla.actualizar_estado(dispositivo, estado)
                    eventos.append(EventoEjecucion(
                        OpIR.SET_STATE.value, f"{dispositivo} ahora {estado}", dispositivo, estado
                    ))
                elif instruccion.op == OpIR.GET_STATE:
                    (dispositivo,) = _textos(instruccion, 1)
                    simbolo = self._tabla.obtener(dispositivo)
                    eventos.append(EventoEjecucion(
                        OpIR.GET_STATE.value, f"{dispositivo} está {simbolo.estado}",
                        dispositivo, simbolo.estado,
                    ))
                elif instruccion.op == OpIR.LIST_DEVICES:
                    _textos(instruccion, 0)
                    dispositivos = tuple(self._tabla.listar())
                    texto = ", ".join(
                        f"{s.identificador} {s.tipo} {s.estado}" for s in dispositivos
                    )
                    eventos.append(EventoEjecucion(
                        OpIR.LIST_DEVICES.value, f"Dispositivos: {texto}", dispositivos=dispositivos
                    ))
                elif instruccion.op == OpIR.COMPARE:
                    dispositivo, operador, estado = _textos(instruccion, 3)
                    if operador != "==":
                        raise ErrorIR(f"Operador de comparación inválido: {operador}")
                    simbolo = self._tabla.obtener(dispositivo)
                    if not self._tabla.estado_valido_para_tipo(simbolo.tipo, estado):
                        raise ErrorIR(f"El estado {estado} no es válido para {dispositivo}")
                    comparacion = simbolo.estado == estado
                elif instruccion.op == OpIR.JUMP_IF_FALSE:
                    if (
                        len(instruccion.args) != 1
                        or type(instruccion.args[0]) is not int
                        or not 0 <= instruccion.args[0] < len(ir)
                    ):
                        raise ErrorIR(f"Destino de salto inválido: {instruccion.args}")
                    if comparacion is None:
                        raise ErrorIR("JUMP_IF_FALSE requiere una comparación previa")
                    if not comparacion:
                        posicion = instruccion.args[0]
                elif instruccion.op == OpIR.NOTIFY:
                    (mensaje,) = _textos(instruccion, 1)
                    self._notificaciones.registrar(mensaje)
                    eventos.append(EventoEjecucion(
                        OpIR.NOTIFY.value, f"Notificación registrada: {mensaje}"
                    ))
                elif instruccion.op == OpIR.SEND_EMAIL:
                    destinatario, mensaje = _textos(instruccion, 2)
                    try:
                        self._correo.enviar(destinatario, mensaje)
                    except ErrorCorreo as error:
                        texto = f"No se pudo enviar el correo a {destinatario}: {error}"
                        errores.append(texto)
                        eventos.append(EventoEjecucion("ERROR_CORREO", texto))
                    else:
                        eventos.append(EventoEjecucion(
                            OpIR.SEND_EMAIL.value, f"Correo enviado a {destinatario}"
                        ))
                else:
                    raise ErrorIR(f"Operación de IR desconocida: {instruccion.op}")
        except (ErrorIR, ErrorTablaSimbolos) as error:
            texto = str(error)
            errores.append(texto)
            eventos.append(EventoEjecucion("ERROR_EJECUCION", texto))

        return ResultadoEjecucion(eventos, not errores, errores)
