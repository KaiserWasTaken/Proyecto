"""Pruebas de optimización y conservación del flujo del IR."""

import pytest

from app.ir.generator import generar_ir
from app.ir.instructions import InstruccionIR, OpIR
from app.optimizer.optimizer import optimizar


def control(dispositivo: str, operacion: str) -> dict[str, object]:
    """Construye una instrucción semántica de control para los ejemplos."""
    return {"tipo": "CONTROL_DISPOSITIVO", "operacion": operacion, "dispositivo": dispositivo}


def test_asignacion_redundante() -> None:
    """Un segundo estado idéntico se elimina con una explicación."""
    ir = generar_ir([control("led1", "ENCENDER"), control("led1", "ENCENDER")])
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == [
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")), InstruccionIR(OpIR.HALT)
    ]
    assert len(resultado.cambios) == 1
    assert "Índice 1" in resultado.cambios[0]
    assert "SET_STATE led1 ENCENDIDO" in resultado.cambios[0]
    assert "redundante" in resultado.cambios[0]
    assert len(ir) == 3


def test_asignacion_sobrescrita() -> None:
    """Se elimina el estado anterior si no se observó antes del siguiente."""
    ir = generar_ir([control("led1", "ENCENDER"), control("led1", "APAGAR")])
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == [
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")), InstruccionIR(OpIR.HALT)
    ]
    assert len(resultado.cambios) == 1
    assert "Índice 0" in resultado.cambios[0]
    assert "sobrescrita" in resultado.cambios[0]


@pytest.mark.parametrize(
    "barrera",
    [
        InstruccionIR(OpIR.GET_STATE, ("led1",)),
        InstruccionIR(OpIR.GET_STATE, ("led2",)),
        InstruccionIR(OpIR.COMPARE, ("led1", "==", "ENCENDIDO")),
        InstruccionIR(OpIR.LIST_DEVICES),
        InstruccionIR(OpIR.NOTIFY, ("x",)),
        InstruccionIR(OpIR.SEND_EMAIL, ("a@b.com", "x")),
        InstruccionIR(OpIR.HALT),
    ],
)
def test_operaciones_observables_son_barreras(barrera: InstruccionIR) -> None:
    """Ninguna lectura, efecto externo ni HALT se cruza o elimina."""
    ir = [
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
        barrera,
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.HALT),
    ]
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == ir
    assert resultado.cambios == []


def test_asignaciones_a_otro_dispositivo_no_son_barrera() -> None:
    """Se elimina solo la asignación sobrescrita al mismo dispositivo."""
    ir = generar_ir([
        control("led1", "ENCENDER"),
        control("led2", "ENCENDER"),
        control("led1", "APAGAR"),
    ])
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == [
        InstruccionIR(OpIR.SET_STATE, ("led2", "ENCENDIDO")),
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.HALT),
    ]
    assert len(resultado.cambios) == 1
    assert "Índice 0" in resultado.cambios[0]


def test_no_fusiona_fuera_y_dentro_del_condicional() -> None:
    """El salto separa la acción condicional de la asignación anterior."""
    ir = generar_ir([
        control("led1", "ENCENDER"),
        {
            "tipo": "CONDICIONAL",
            "dispositivo": "led2",
            "estado": "ENCENDIDO",
            "accion": control("led1", "APAGAR"),
        },
    ])
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == ir
    assert resultado.cambios == []


def test_correos_repetidos_no_se_eliminan() -> None:
    """Dos envíos idénticos siguen presentes y en orden."""
    correo = InstruccionIR(OpIR.SEND_EMAIL, ("a@b.com", "Hola"))
    ir = [correo, correo, InstruccionIR(OpIR.HALT)]
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == ir
    assert resultado.cambios == []


def test_reajusta_salto_al_eliminar_instrucciones_anteriores() -> None:
    """Un salto mantiene su destino original después de compactar el IR."""
    ir = generar_ir([
        control("led1", "ENCENDER"),
        control("led1", "APAGAR"),
        {
            "tipo": "CONDICIONAL",
            "dispositivo": "led2",
            "estado": "ENCENDIDO",
            "accion": control("led1", "ENCENDER"),
        },
        {"tipo": "NOTIFICACION", "mensaje": "después"},
    ])
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == [
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.GET_STATE, ("led2",)),
        InstruccionIR(OpIR.COMPARE, ("led2", "==", "ENCENDIDO")),
        InstruccionIR(OpIR.JUMP_IF_FALSE, (5,)),
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
        InstruccionIR(OpIR.NOTIFY, ("después",)),
        InstruccionIR(OpIR.HALT),
    ]
    assert len(resultado.cambios) == 1


def test_destino_eliminado_se_reajusta_a_la_siguiente_instruccion() -> None:
    """Si un destino se sobrescribe en su bloque, apunta a su sucesor conservado."""
    ir = [
        InstruccionIR(OpIR.JUMP_IF_FALSE, (2,)),
        InstruccionIR(OpIR.SET_STATE, ("led2", "APAGADO")),
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.HALT),
    ]
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == [
        InstruccionIR(OpIR.JUMP_IF_FALSE, (2,)),
        InstruccionIR(OpIR.SET_STATE, ("led2", "APAGADO")),
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.HALT),
    ]
    assert len(resultado.cambios) == 1


def test_destino_de_salto_inicia_nuevo_bloque() -> None:
    """Una asignación anterior a un destino no se compara con el destino."""
    ir = [
        InstruccionIR(OpIR.JUMP_IF_FALSE, (2,)),
        InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")),
        InstruccionIR(OpIR.SET_STATE, ("led1", "APAGADO")),
        InstruccionIR(OpIR.HALT),
    ]
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == ir
    assert resultado.cambios == []


def test_opciones_controlan_cada_optimizacion() -> None:
    """Desactivar una regla conserva su caso sin desactivar la otra."""
    repetida = generar_ir([control("led1", "ENCENDER"), control("led1", "ENCENDER")])
    sobrescrita = generar_ir([control("led1", "ENCENDER"), control("led1", "APAGAR")])
    assert optimizar(repetida, eliminar_redundantes=False).ir_optimizado == repetida
    assert optimizar(sobrescrita, eliminar_sobrescritas=False).ir_optimizado == sobrescrita
    assert len(optimizar(repetida, eliminar_sobrescritas=False).cambios) == 1
    assert len(optimizar(sobrescrita, eliminar_redundantes=False).cambios) == 1
    assert optimizar(repetida, eliminar_redundantes=False, eliminar_sobrescritas=False).cambios == []


def test_programa_sin_optimizaciones() -> None:
    """Un programa sin asignaciones repetidas permanece igual."""
    ir = generar_ir([control("led1", "ENCENDER"), {"tipo": "CONSULTA", "dispositivo": "led1"}])
    resultado = optimizar(ir)
    assert resultado.ir_optimizado == ir
    assert resultado.cambios == []


@pytest.mark.parametrize("destino", [-1, 2, "1"])
def test_destino_invalido_no_se_oculta(destino: int | str) -> None:
    """El optimizador rechaza saltos fuera del IR o sin índice entero."""
    ir = [InstruccionIR(OpIR.JUMP_IF_FALSE, (destino,)), InstruccionIR(OpIR.HALT)]
    with pytest.raises(ValueError, match="Destino de salto inválido"):
        optimizar(ir)


@pytest.mark.skip(reason="pendiente del ejecutor (Paso 3)")
def test_equivalencia_con_y_sin_optimizacion() -> None:
    """Comparará el estado final y los efectos observables con el ejecutor."""
