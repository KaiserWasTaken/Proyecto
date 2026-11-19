"""Optimizaciones de asignaciones dentro de bloques básicos.

Se preservan el estado final de los dispositivos y las salidas de GET_STATE,
LIST_DEVICES, NOTIFY y SEND_EMAIL, en el mismo orden. Los estados intermedios
de SET_STATE no son observables: no se registra un evento por cada asignación.
"""

from dataclasses import dataclass

from app.ir.instructions import InstruccionIR, OpIR


@dataclass(frozen=True)
class ResultadoOptimizacion:
    """IR optimizado y descripción de cada instrucción eliminada."""

    ir_optimizado: list[InstruccionIR]
    cambios: list[str]


def _destino_salto(instruccion: InstruccionIR, longitud: int) -> int:
    """Devuelve el destino absoluto de un salto o rechaza un IR inválido."""
    if len(instruccion.args) != 1:
        raise ValueError("JUMP_IF_FALSE requiere un único destino")
    destino = instruccion.args[0]
    if type(destino) is not int or not 0 <= destino < longitud:
        raise ValueError(f"Destino de salto inválido: {destino}")
    return destino


def optimizar(
    ir: list[InstruccionIR],
    *,
    eliminar_redundantes: bool = True,
    eliminar_sobrescritas: bool = True,
) -> ResultadoOptimizacion:
    """Optimiza asignaciones sin cruzar saltos, destinos ni efectos observables."""
    destinos = {
        _destino_salto(instruccion, len(ir))
        for instruccion in ir
        if instruccion.op == OpIR.JUMP_IF_FALSE
    }
    pendientes: dict[str, list[int]] = {}
    eliminados: set[int] = set()
    cambios: list[str] = []

    for indice, instruccion in enumerate(ir):
        if indice in destinos:
            pendientes.clear()

        if instruccion.op != OpIR.SET_STATE:
            pendientes.clear()
            continue

        if len(instruccion.args) != 2:
            raise ValueError("SET_STATE requiere un dispositivo y un estado de texto")
        dispositivo, estado = instruccion.args
        if not isinstance(dispositivo, str) or not isinstance(estado, str):
            raise ValueError("SET_STATE requiere un dispositivo y un estado de texto")
        anteriores = pendientes.get(dispositivo, [])
        if anteriores:
            ultimo = ir[anteriores[-1]]
            if ultimo.args[1] == estado and eliminar_redundantes:
                eliminados.add(indice)
                cambios.append(f"Índice {indice}: {instruccion} eliminado por ser redundante")
                continue
            if ultimo.args[1] != estado and eliminar_sobrescritas:
                for anterior in anteriores:
                    eliminados.add(anterior)
                    cambios.append(
                        f"Índice {anterior}: {ir[anterior]} eliminado por asignación sobrescrita "
                        f"en índice {indice}"
                    )
                anteriores = []
        anteriores.append(indice)
        pendientes[dispositivo] = anteriores

    posiciones: dict[int, int] = {}
    optimizado: list[InstruccionIR] = []
    for indice, instruccion in enumerate(ir):
        posiciones[indice] = len(optimizado)
        if indice not in eliminados:
            optimizado.append(instruccion)

    for indice, instruccion in enumerate(optimizado):
        if instruccion.op == OpIR.JUMP_IF_FALSE:
            destino_original = _destino_salto(instruccion, len(ir))
            optimizado[indice] = InstruccionIR(
                OpIR.JUMP_IF_FALSE, (posiciones[destino_original],)
            )

    return ResultadoOptimizacion(optimizado, cambios)
