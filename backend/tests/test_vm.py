"""Pruebas del ejecutor con puertos falsos en memoria."""

import pytest

from app.ir.instructions import InstruccionIR, OpIR
from app.semantic.symbol_table import DispositivoRepositoryMemoria, TablaSimbolos
from app.vm.executor import Ejecutor, EventoEjecucion, MAXIMO_INSTRUCCIONES
from conftest import CorreoFalso, NotificacionesFalsas, compilar, repositorio_inicial


def estado_actual(repositorio: DispositivoRepositoryMemoria, dispositivo: str) -> str:
    """Obtiene el estado de un dispositivo que debe existir en la prueba."""
    return TablaSimbolos(repositorio).obtener(dispositivo).estado


@pytest.mark.parametrize(
    ("fuente", "dispositivo", "estado"),
    [
        ("ENCENDER led1", "led1", "ENCENDIDO"),
        ("APAGAR led1", "led1", "APAGADO"),
        ("ACTIVAR alarma1", "alarma1", "ACTIVADA"),
        ("DESACTIVAR alarma1", "alarma1", "DESACTIVADA"),
    ],
)
def test_control_individual(fuente: str, dispositivo: str, estado: str) -> None:
    """Cada operación deja el estado solicitado y produce su evento."""
    repositorio = repositorio_inicial()
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(
        compilar(fuente, repositorio)
    )
    assert resultado.exito
    assert estado_actual(repositorio, dispositivo) == estado
    assert resultado.eventos == [
        EventoEjecucion("SET_STATE", f"{dispositivo} ahora {estado}", dispositivo, estado)
    ]


def test_encender_y_apagar() -> None:
    """Las asignaciones actualizan el repositorio y emiten eventos ordenados."""
    repositorio = repositorio_inicial()
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(
        compilar("ENCENDER led1\nAPAGAR led1", repositorio)
    )
    assert resultado.exito and not resultado.errores
    assert estado_actual(repositorio, "led1") == "APAGADO"
    assert resultado.eventos == [
        EventoEjecucion("SET_STATE", "led1 ahora ENCENDIDO", "led1", "ENCENDIDO"),
        EventoEjecucion("SET_STATE", "led1 ahora APAGADO", "led1", "APAGADO"),
    ]


def test_activar_y_desactivar_alarma() -> None:
    """Los estados de una alarma se actualizan con sus nombres de dominio."""
    repositorio = repositorio_inicial()
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(
        compilar("DESACTIVAR alarma1\nACTIVAR alarma1", repositorio)
    )
    assert resultado.exito
    assert estado_actual(repositorio, "alarma1") == "ACTIVADA"
    assert [evento.estado for evento in resultado.eventos] == ["DESACTIVADA", "ACTIVADA"]


def test_consultar_no_cambia_estado() -> None:
    """Una consulta devuelve el estado actual sin modificar el dispositivo."""
    repositorio = repositorio_inicial()
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(
        compilar("CONSULTAR led1", repositorio)
    )
    assert resultado.exito
    assert resultado.eventos == [EventoEjecucion("GET_STATE", "led1 está APAGADO", "led1", "APAGADO")]
    assert estado_actual(repositorio, "led1") == "APAGADO"


def test_listar_devuelve_instantanea_de_cuatro_dispositivos() -> None:
    """El evento del listado conserva identificador, tipo y estado de cada dispositivo."""
    repositorio = repositorio_inicial()
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(
        compilar("LISTAR DISPOSITIVOS\nENCENDER led1", repositorio)
    )
    assert resultado.exito
    listado = resultado.eventos[0]
    assert listado.tipo == "LIST_DEVICES"
    assert listado.dispositivos is not None
    assert [(s.identificador, s.tipo, s.estado) for s in listado.dispositivos] == [
        ("led1", "LED", "APAGADO"),
        ("led2", "LED", "ENCENDIDO"),
        ("alarma1", "ALARMA", "ACTIVADA"),
        ("ventilador1", "VENTILADOR", "APAGADO"),
    ]


def test_notificacion_y_correo() -> None:
    """Los puertos reciben exactamente el contenido de cada instrucción."""
    repositorio = repositorio_inicial()
    correo, notificaciones = CorreoFalso(), NotificacionesFalsas()
    resultado = Ejecutor(repositorio, correo, notificaciones).ejecutar(compilar(
        'NOTIFICAR "Prueba"\nENVIAR CORREO A "a@b.com" MENSAJE "Hola"', repositorio
    ))
    assert resultado.exito
    assert notificaciones.mensajes == ["Prueba"]
    assert correo.enviados == [("a@b.com", "Hola")]
    assert [evento.texto for evento in resultado.eventos] == [
        "Notificación registrada: Prueba", "Correo enviado a a@b.com"
    ]


@pytest.mark.parametrize(("estado_inicial", "eventos_control"), [("ENCENDIDO", 1), ("APAGADO", 0)])
def test_condicional_verdadero_y_falso(estado_inicial: str, eventos_control: int) -> None:
    """El cuerpo se ejecuta únicamente cuando la comparación es verdadera."""
    repositorio = repositorio_inicial()
    repositorio.actualizar_estado("led1", estado_inicial)
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(
        compilar("SI led1 == ENCENDIDO ENTONCES APAGAR led1", repositorio)
    )
    assert resultado.exito
    assert estado_actual(repositorio, "led1") == "APAGADO"
    assert [evento.tipo for evento in resultado.eventos].count("SET_STATE") == eventos_control
    assert resultado.eventos[0].estado == estado_inicial


def test_condicional_notifica_alarma_activa() -> None:
    """Una condición verdadera puede ejecutar una notificación."""
    repositorio = repositorio_inicial()
    notificaciones = NotificacionesFalsas()
    resultado = Ejecutor(repositorio, CorreoFalso(), notificaciones).ejecutar(compilar(
        'SI alarma1 == ACTIVADA ENTONCES NOTIFICAR "Alarma activada"', repositorio
    ))
    assert resultado.exito
    assert notificaciones.mensajes == ["Alarma activada"]


def test_programa_varias_lineas() -> None:
    """Las asignaciones se ejecutan y registran en el orden de la fuente."""
    repositorio = repositorio_inicial()
    fuente = "ENCENDER led1\nENCENDER led2\nDESACTIVAR alarma1"
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(
        compilar(fuente, repositorio)
    )
    assert resultado.exito
    assert [estado_actual(repositorio, d) for d in ("led1", "led2", "alarma1")] == [
        "ENCENDIDO", "ENCENDIDO", "DESACTIVADA"
    ]
    assert [evento.texto for evento in resultado.eventos] == [
        "led1 ahora ENCENDIDO", "led2 ahora ENCENDIDO", "alarma1 ahora DESACTIVADA"
    ]


def test_fallo_correo_continua_y_marca_resultado() -> None:
    """Un ErrorCorreo se registra y no impide las instrucciones posteriores."""
    repositorio = repositorio_inicial()
    notificaciones = NotificacionesFalsas()
    resultado = Ejecutor(repositorio, CorreoFalso(fallar=True), notificaciones).ejecutar(compilar(
        'ENVIAR CORREO A "a@b.com" MENSAJE "Hola"\nNOTIFICAR "siguiente"\nENCENDER led1',
        repositorio,
    ))
    error = "No se pudo enviar el correo a a@b.com: servicio no disponible"
    assert not resultado.exito
    assert resultado.errores == [error]
    assert [evento.texto for evento in resultado.eventos] == [
        error, "Notificación registrada: siguiente", "led1 ahora ENCENDIDO"
    ]
    assert resultado.eventos[0].tipo == "ERROR_CORREO"
    assert notificaciones.mensajes == ["siguiente"]
    assert estado_actual(repositorio, "led1") == "ENCENDIDO"


def test_limite_interrumpe_bucle() -> None:
    """Un salto hacia sí mismo termina con un error controlado."""
    repositorio = repositorio_inicial()
    ir = [
        InstruccionIR(OpIR.COMPARE, ("led1", "==", "ENCENDIDO")),
        InstruccionIR(OpIR.JUMP_IF_FALSE, (1,)),
        InstruccionIR(OpIR.HALT),
    ]
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(ir)
    assert not resultado.exito
    assert f"límite de {MAXIMO_INSTRUCCIONES} instrucciones" in resultado.errores[0]
    assert resultado.eventos[-1].tipo == "ERROR_EJECUCION"


@pytest.mark.parametrize(
    ("instruccion", "mensaje"),
    [
        (InstruccionIR(OpIR.SET_STATE, ("inexistente", "ENCENDIDO")), "inexistente no existe"),
        (InstruccionIR(OpIR.SET_STATE, ("alarma1", "ENCENDIDO")), "no es válido para el tipo ALARMA"),
        (InstruccionIR(OpIR.GET_STATE, ("inexistente",)), "inexistente no existe"),
        (InstruccionIR(OpIR.COMPARE, ("inexistente", "==", "ENCENDIDO")), "inexistente no existe"),
        (InstruccionIR(OpIR.JUMP_IF_FALSE, (9,)), "Destino de salto inválido"),
        (InstruccionIR(OpIR.JUMP_IF_FALSE, (1,)), "requiere una comparación previa"),
        (InstruccionIR(OpIR.SET_STATE, ("led1",)), "Argumentos inválidos"),
    ],
)
def test_ir_invalido_aborta_sin_excepcion(instruccion: InstruccionIR, mensaje: str) -> None:
    """Los errores de IR y de dispositivo impiden ejecutar instrucciones posteriores."""
    repositorio = repositorio_inicial()
    ir = [instruccion, InstruccionIR(OpIR.SET_STATE, ("led1", "ENCENDIDO")), InstruccionIR(OpIR.HALT)]
    resultado = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas()).ejecutar(ir)
    assert not resultado.exito
    assert mensaje in resultado.errores[0]
    assert resultado.eventos[-1].tipo == "ERROR_EJECUCION"
    assert estado_actual(repositorio, "led1") == "APAGADO"


def test_comparacion_no_persiste_entre_ejecuciones() -> None:
    """Cada llamada empieza con el registro de comparación sin inicializar."""
    repositorio = repositorio_inicial()
    ejecutor = Ejecutor(repositorio, CorreoFalso(), NotificacionesFalsas())
    assert ejecutor.ejecutar(compilar("SI led1 == APAGADO ENTONCES ENCENDER led1", repositorio)).exito
    resultado = ejecutor.ejecutar([InstruccionIR(OpIR.JUMP_IF_FALSE, (1,)), InstruccionIR(OpIR.HALT)])
    assert not resultado.exito
    assert "requiere una comparación previa" in resultado.errores[0]
