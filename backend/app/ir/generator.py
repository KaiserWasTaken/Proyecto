"""Traducción de instrucciones semánticas a representación intermedia."""

from app.ir.instructions import InstruccionIR, OpIR
from app.semantic.actions import verificar_repeticion


_ESTADOS_CONTROL = {
    "ENCENDER": "ENCENDIDO",
    "APAGAR": "APAGADO",
    "ACTIVAR": "ACTIVADA",
    "DESACTIVAR": "DESACTIVADA",
}


def _texto(instruccion: dict[str, object], clave: str) -> str:
    """Obtiene un argumento textual o rechaza una entrada mal formada."""
    valor = instruccion.get(clave)
    if not isinstance(valor, str):
        raise ValueError(f"Se esperaba texto en el campo {clave}")
    return valor


def _accion(instruccion: dict[str, object]) -> dict[str, object]:
    """Obtiene el diccionario de una acción anidada."""
    accion = instruccion.get("accion")
    if not isinstance(accion, dict) or not all(isinstance(clave, str) for clave in accion):
        raise ValueError("Se esperaba un diccionario de acción con claves de texto")
    return accion


def _traducir(instruccion: dict[str, object], salida: list[InstruccionIR]) -> None:
    """Añade el IR de una instrucción usando índices absolutos de salida."""
    tipo = _texto(instruccion, "tipo")
    if tipo == "CONTROL_DISPOSITIVO":
        operacion = _texto(instruccion, "operacion")
        if operacion not in _ESTADOS_CONTROL:
            raise ValueError(f"Operación de control desconocida: {operacion}")
        salida.append(InstruccionIR(OpIR.SET_STATE, (_texto(instruccion, "dispositivo"), _ESTADOS_CONTROL[operacion])))
    elif tipo == "CONSULTA":
        salida.append(InstruccionIR(OpIR.GET_STATE, (_texto(instruccion, "dispositivo"),)))
    elif tipo == "LISTADO":
        salida.append(InstruccionIR(OpIR.LIST_DEVICES))
    elif tipo == "NOTIFICACION":
        salida.append(InstruccionIR(OpIR.NOTIFY, (_texto(instruccion, "mensaje"),)))
    elif tipo == "CORREO":
        salida.append(InstruccionIR(OpIR.SEND_EMAIL, (
            _texto(instruccion, "destinatario"), _texto(instruccion, "mensaje")
        )))
    elif tipo == "CONDICIONAL":
        dispositivo = _texto(instruccion, "dispositivo")
        estado = _texto(instruccion, "estado")
        salida.append(InstruccionIR(OpIR.GET_STATE, (dispositivo,)))
        salida.append(InstruccionIR(OpIR.COMPARE, (dispositivo, "==", estado)))
        posicion_salto = len(salida)
        salida.append(InstruccionIR(OpIR.JUMP_IF_FALSE, (0,)))
        _traducir(_accion(instruccion), salida)
        salida[posicion_salto] = InstruccionIR(OpIR.JUMP_IF_FALSE, (len(salida),))
    elif tipo == "REPETIR":
        veces = instruccion.get("veces")
        if type(veces) is not int or not verificar_repeticion(veces):
            raise ValueError("El número de repeticiones debe estar entre 1 y 100")
        accion = _accion(instruccion)
        for _ in range(veces):
            _traducir(accion, salida)
    else:
        raise ValueError(f"Tipo de instrucción desconocido: {tipo}")


def generar_ir(instrucciones: list[dict[str, object]]) -> list[InstruccionIR]:
    """Traduce instrucciones semánticas válidas y termina el programa con HALT."""
    salida: list[InstruccionIR] = []
    for instruccion in instrucciones:
        _traducir(instruccion, salida)
    salida.append(InstruccionIR(OpIR.HALT))
    return salida
