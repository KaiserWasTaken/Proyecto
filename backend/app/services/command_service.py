"""Servicio de consulta de dispositivos y validación de comandos."""

from typing import Literal, TypedDict

from app.lexer.errors import ErrorLexico
from app.parser.errors import ErrorSintactico
from app.semantic.analyzer import Analizador, ErrorSemantico
from app.semantic.symbol_table import DispositivoRepository
from app.services.frontend_pipeline import analizar


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
