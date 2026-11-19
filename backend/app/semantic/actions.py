"""Acciones de consulta y construcción para el análisis semántico."""

from app.ast.nodes import (
    Condicional,
    Consultar,
    ControlDispositivo,
    EnviarCorreo,
    Instruccion,
    Listar,
    Notificar,
    Repetir,
)
from app.semantic.symbol_table import TablaSimbolos


def verificar_dispositivo(identificador: str, tabla: TablaSimbolos) -> bool:
    """Indica si el identificador existe, respetando mayúsculas y minúsculas."""
    return tabla.existe(identificador)


def verificar_operacion(operacion: str, identificador: str, tabla: TablaSimbolos) -> bool:
    """Comprueba la operación; la tabla informa si el dispositivo no existe."""
    return tabla.operacion_permitida(identificador, operacion)


def verificar_estado(identificador: str, estado: str, tabla: TablaSimbolos) -> bool:
    """Comprueba el estado para el tipo; la tabla informa si el dispositivo no existe."""
    simbolo = tabla.obtener(identificador)
    return tabla.estado_valido_para_tipo(simbolo.tipo, estado)


def construir_instruccion(instruccion: Instruccion) -> dict[str, object]:
    """Construye la representación de una instrucción previamente validada.

    Esta función no valida ni ejecuta instrucciones; el analizador debe
    validar también las acciones anidadas antes de llamar a esta función.
    """
    if isinstance(instruccion, ControlDispositivo):
        return {
            "tipo": "CONTROL_DISPOSITIVO",
            "operacion": instruccion.operacion.value,
            "dispositivo": instruccion.dispositivo,
        }
    if isinstance(instruccion, Consultar):
        return {"tipo": "CONSULTA", "dispositivo": instruccion.dispositivo}
    if isinstance(instruccion, Listar):
        return {"tipo": "LISTADO"}
    if isinstance(instruccion, Notificar):
        return {"tipo": "NOTIFICACION", "mensaje": instruccion.mensaje}
    if isinstance(instruccion, EnviarCorreo):
        return {
            "tipo": "CORREO",
            "destinatario": instruccion.destinatario,
            "mensaje": instruccion.mensaje,
        }
    if isinstance(instruccion, Condicional):
        return {
            "tipo": "CONDICIONAL",
            "dispositivo": instruccion.dispositivo,
            "estado": instruccion.estado,
            "accion": construir_instruccion(instruccion.accion),
        }
    if isinstance(instruccion, Repetir):
        return {
            "tipo": "REPETIR",
            "veces": instruccion.veces,
            "accion": construir_instruccion(instruccion.accion),
        }
    raise TypeError(f"Instrucción no compatible: {type(instruccion).__name__}")
