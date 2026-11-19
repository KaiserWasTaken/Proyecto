"""Análisis semántico de instrucciones sin ejecución ni cambios de estado."""

from dataclasses import dataclass

from app.ast.nodes import (
    Condicional,
    Consultar,
    ControlDispositivo,
    EnviarCorreo,
    Listar,
    Nodo,
    NodoVisitor,
    Notificar,
    Programa,
    Repetir,
)
from app.semantic.actions import (
    construir_instruccion,
    verificar_correo,
    verificar_dispositivo,
    verificar_estado,
    verificar_mensaje,
    verificar_operacion,
    verificar_repeticion,
)
from app.semantic.symbol_table import DispositivoRepository, TablaSimbolos


@dataclass(frozen=True)
class ErrorSemantico:
    """Diagnóstico semántico con código y posición del nodo de origen."""

    codigo: str
    mensaje: str
    linea: int
    columna: int

    def __str__(self) -> str:
        """Presenta la posición y el mensaje de forma legible."""
        return f"Error semántico (línea {self.linea}, col {self.columna}): {self.mensaje}"


class Analizador(NodoVisitor[None]):
    """Valida un AST mediante acciones sobre un repositorio inyectado."""

    def __init__(self, repositorio: DispositivoRepository) -> None:
        """Crea una tabla sobre el repositorio suministrado sin añadir dispositivos."""
        self._tabla = TablaSimbolos(repositorio)
        self._errores: list[ErrorSemantico] = []
        self._instrucciones: list[dict[str, object]] = []

    def analizar(self, programa: Programa) -> tuple[list[dict[str, object]], list[ErrorSemantico]]:
        """Devuelve las instrucciones válidas y todos los errores del programa."""
        self._errores = []
        self._instrucciones = []
        programa.accept(self)
        return self._instrucciones, self._errores

    def _error(self, nodo: Nodo, codigo: str, mensaje: str) -> None:
        """Añade un diagnóstico situado en el inicio del nodo."""
        self._errores.append(ErrorSemantico(codigo, mensaje, nodo.linea, nodo.columna))

    def _verificar_dispositivo(self, nodo: Nodo, identificador: str) -> bool:
        """Comprueba la existencia e informa del dispositivo ausente."""
        if verificar_dispositivo(identificador, self._tabla):
            return True
        self._error(nodo, "DISPOSITIVO_NO_EXISTE", f"El dispositivo {identificador} no existe")
        return False

    def _verificar_operacion(self, nodo: Nodo, identificador: str, operacion: str) -> None:
        """Comprueba existencia y compatibilidad sin errores en cascada."""
        if self._verificar_dispositivo(nodo, identificador):
            if not verificar_operacion(operacion, identificador, self._tabla):
                self._error(
                    nodo,
                    "OPERACION_INCOMPATIBLE",
                    f"La operación {operacion} no está permitida para {identificador}",
                )

    def visit_programa(self, nodo: Programa) -> None:
        """Valida todas las instrucciones y construye solo las válidas."""
        for instruccion in nodo.instrucciones:
            errores_anteriores = len(self._errores)
            instruccion.accept(self)
            if len(self._errores) == errores_anteriores:
                self._instrucciones.append(construir_instruccion(instruccion))

    def visit_control_dispositivo(self, nodo: ControlDispositivo) -> None:
        """Valida la operación de control sobre el dispositivo."""
        self._verificar_operacion(nodo, nodo.dispositivo, nodo.operacion.value)

    def visit_consultar(self, nodo: Consultar) -> None:
        """Valida la consulta sobre el dispositivo."""
        self._verificar_operacion(nodo, nodo.dispositivo, "CONSULTAR")

    def visit_listar(self, nodo: Listar) -> None:
        """Acepta un listado, ya que el parser exige DISPOSITIVOS."""

    def visit_notificar(self, nodo: Notificar) -> None:
        """Comprueba que la notificación tenga contenido."""
        if not verificar_mensaje(nodo.mensaje):
            self._error(nodo, "MENSAJE_VACIO", "El mensaje de la notificación está vacío")

    def visit_enviar_correo(self, nodo: EnviarCorreo) -> None:
        """Comprueba el destinatario y el contenido del correo."""
        if not verificar_correo(nodo.destinatario, nodo.mensaje):
            self._error(nodo, "CORREO_INVALIDO", "El destinatario o el mensaje del correo no es válido")

    def visit_condicional(self, nodo: Condicional) -> None:
        """Valida la condición y visita su acción, incluso si falla la condición."""
        if self._verificar_dispositivo(nodo, nodo.dispositivo):
            if not verificar_estado(nodo.dispositivo, nodo.estado, self._tabla):
                self._error(
                    nodo,
                    "ESTADO_INCOMPATIBLE",
                    f"El estado {nodo.estado} no es válido para {nodo.dispositivo}",
                )
        nodo.accion.accept(self)

    def visit_repetir(self, nodo: Repetir) -> None:
        """Valida la cantidad y visita la acción de la repetición."""
        if not verificar_repeticion(nodo.veces):
            self._error(nodo, "REPETICION_INVALIDA", "El número de repeticiones debe ser mayor que cero")
        nodo.accion.accept(self)
