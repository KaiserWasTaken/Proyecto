"""Servicio de consulta, validación y ejecución transaccional de comandos."""

import logging
from typing import Literal, NotRequired, TypedDict

from sqlalchemy.orm import Session

from app.db.repositorios import (
    PostgresDispositivoRepository,
    PostgresRegistroNotificaciones,
    RepositorioEjecuciones,
)
from app.ir.generator import generar_ir
from app.lexer.errors import ErrorLexico
from app.optimizer.optimizer import optimizar
from app.parser.errors import ErrorSintactico
from app.semantic.analyzer import Analizador, ErrorSemantico
from app.semantic.symbol_table import DispositivoRepository
from app.services.frontend_pipeline import analizar
from app.vm.executor import Ejecutor, EventoEjecucion
from app.vm.ports import ServicioCorreo


_logger = logging.getLogger(__name__)


class DatosDispositivo(TypedDict):
    """Información pública de un dispositivo."""

    identificador: str
    tipo: str
    estado: str
    operaciones: list[str]


class DatosError(TypedDict):
    """Diagnóstico normalizado de una fase del lenguaje."""

    fase: Literal["lexico", "sintactico", "semantico"]
    codigo: str
    mensaje: str
    linea: int
    columna: int


class ResultadoValidacion(TypedDict):
    """Resultado del servicio de validación."""

    valido: bool
    errores: list[DatosError]
    instrucciones: list[dict[str, object]]


class DatosEvento(TypedDict):
    """Evento de ejecución enviado a la API y al historial."""

    tipo: str
    texto: str
    dispositivo: NotRequired[str]
    estado: NotRequired[str]


class ResultadoComando(TypedDict):
    """Validación y resultado de ejecutar un programa completo."""

    valido: bool
    exito: bool
    errores: list[DatosError]
    eventos: list[DatosEvento]


def listar_dispositivos(repositorio: DispositivoRepository) -> list[DatosDispositivo]:
    """Devuelve los dispositivos y sus operaciones sin modificar el repositorio."""
    return [
        {
            "identificador": simbolo.identificador,
            "tipo": simbolo.tipo,
            "estado": simbolo.estado,
            "operaciones": sorted(simbolo.operaciones_permitidas),
        }
        for simbolo in repositorio.listar()
    ]


def _datos_error(
    fase: Literal["lexico", "sintactico", "semantico"],
    error: ErrorLexico | ErrorSintactico | ErrorSemantico,
) -> DatosError:
    """Convierte un diagnóstico del lenguaje a la estructura de respuesta."""
    return {
        "fase": fase,
        "codigo": error.codigo,
        "mensaje": error.mensaje,
        "linea": error.linea,
        "columna": error.columna,
    }


def validar_comandos(fuente: str, repositorio: DispositivoRepository) -> ResultadoValidacion:
    """Valida el texto por fases sin ejecutar instrucciones ni alterar estados."""
    resultado = analizar(fuente)
    if resultado.tiene_errores:
        errores = [_datos_error("lexico", error) for error in resultado.errores_lexicos]
        errores.extend(_datos_error("sintactico", error) for error in resultado.errores_sintacticos)
        return {"valido": False, "errores": errores, "instrucciones": []}

    instrucciones, errores_semanticos = Analizador(repositorio).analizar(resultado.programa)
    return {
        "valido": not errores_semanticos,
        "errores": [_datos_error("semantico", error) for error in errores_semanticos],
        "instrucciones": instrucciones,
    }


def _datos_evento(evento: EventoEjecucion) -> DatosEvento:
    """Adapta los datos públicos de un evento al contrato HTTP."""
    datos: DatosEvento = {"tipo": evento.tipo, "texto": evento.texto}
    if evento.dispositivo is not None:
        datos["dispositivo"] = evento.dispositivo
    if evento.estado is not None:
        datos["estado"] = evento.estado
    return datos


def ejecutar_comandos(fuente: str, sesion: Session, correo: ServicioCorreo) -> ResultadoComando:
    """Valida, ejecuta y guarda el resultado con una transacción por ejecución."""
    repositorio = PostgresDispositivoRepository(sesion)
    historial = RepositorioEjecuciones(sesion)
    validacion = validar_comandos(fuente, repositorio)
    if not validacion["valido"]:
        historial.guardar(fuente, False, [])
        sesion.commit()
        return {"valido": False, "exito": False, "errores": validacion["errores"], "eventos": []}

    try:
        ir = optimizar(generar_ir(validacion["instrucciones"])).ir_optimizado
        ejecutor = Ejecutor(repositorio, correo, PostgresRegistroNotificaciones(sesion))
        ejecucion = ejecutor.ejecutar(ir)
    except Exception:
        _logger.exception("La ejecución del programa abortó por un error inesperado")
        sesion.rollback()
        eventos: list[DatosEvento] = [{
            "tipo": "ERROR_EJECUCION",
            "texto": "Error interno: se abortó la ejecución y se revirtieron los cambios de la base de datos",
        }]
        exito = False
    else:
        eventos = [_datos_evento(evento) for evento in ejecucion.eventos]
        exito = ejecucion.exito
        if any(evento.tipo == "ERROR_EJECUCION" for evento in ejecucion.eventos):
            sesion.rollback()
            exito = False
            eventos.append({
                "tipo": "ERROR_EJECUCION",
                "texto": "Se abortó la ejecución y se revirtieron los cambios de la base de datos",
            })

    historial.guardar(fuente, exito, [dict(evento) for evento in eventos])
    sesion.commit()
    return {"valido": True, "exito": exito, "errores": [], "eventos": eventos}
