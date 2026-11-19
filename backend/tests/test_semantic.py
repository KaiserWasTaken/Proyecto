"""Pruebas del analizador semántico y sus resultados."""

from dataclasses import FrozenInstanceError

import pytest

from app.semantic.analyzer import Analizador, ErrorSemantico
from app.semantic.symbol_table import DispositivoRepositoryMemoria, TablaSimbolos
from app.services.frontend_pipeline import analizar as analizar_fuente


@pytest.fixture
def repositorio() -> DispositivoRepositoryMemoria:
    """Crea un repositorio independiente con los dispositivos iniciales."""
    repositorio = DispositivoRepositoryMemoria()
    for simbolo in TablaSimbolos().listar():
        repositorio.registrar(simbolo)
    return repositorio


def analizar_texto(
    fuente: str, repositorio: DispositivoRepositoryMemoria
) -> tuple[list[dict[str, object]], list[ErrorSemantico]]:
    """Analiza texto sintácticamente válido y ejecuta la validación semántica."""
    resultado = analizar_fuente(fuente)
    assert not resultado.tiene_errores
    return Analizador(repositorio).analizar(resultado.programa)


@pytest.mark.parametrize(
    ("fuente", "esperada"),
    [
        ("ENCENDER led1", {"tipo": "CONTROL_DISPOSITIVO", "operacion": "ENCENDER", "dispositivo": "led1"}),
        ("CONSULTAR led1", {"tipo": "CONSULTA", "dispositivo": "led1"}),
        ("LISTAR DISPOSITIVOS", {"tipo": "LISTADO"}),
        ('NOTIFICAR "Prueba"', {"tipo": "NOTIFICACION", "mensaje": "Prueba"}),
        ('ENVIAR CORREO A "a@b.com" MENSAJE "Hola"',
         {"tipo": "CORREO", "destinatario": "a@b.com", "mensaje": "Hola"}),
        ("SI led1 == ENCENDIDO ENTONCES APAGAR led1",
         {"tipo": "CONDICIONAL", "dispositivo": "led1", "estado": "ENCENDIDO",
          "accion": {"tipo": "CONTROL_DISPOSITIVO", "operacion": "APAGAR", "dispositivo": "led1"}}),
        ("REPETIR 3 VECES ENCENDER led1",
         {"tipo": "REPETIR", "veces": 3,
          "accion": {"tipo": "CONTROL_DISPOSITIVO", "operacion": "ENCENDER", "dispositivo": "led1"}}),
    ],
)
def test_instrucciones_validas(
    repositorio: DispositivoRepositoryMemoria, fuente: str, esperada: dict[str, object]
) -> None:
    """Las instrucciones válidas producen exactamente la estructura solicitada."""
    instrucciones, errores = analizar_texto(fuente, repositorio)
    assert errores == []
    assert instrucciones == [esperada]


@pytest.mark.parametrize(
    ("fuente", "codigo", "columna"),
    [
        ("ENCENDER dispositivo99", "DISPOSITIVO_NO_EXISTE", 1),
        ("ENCENDER LED1", "DISPOSITIVO_NO_EXISTE", 1),
        ("CONSULTAR dispositivo99", "DISPOSITIVO_NO_EXISTE", 1),
        ("ENCENDER alarma1", "OPERACION_INCOMPATIBLE", 1),
        ("ACTIVAR led1", "OPERACION_INCOMPATIBLE", 1),
        ("SI alarma1 == ENCENDIDO ENTONCES APAGAR led1", "ESTADO_INCOMPATIBLE", 1),
        ("SI dispositivo99 == ENCENDIDO ENTONCES APAGAR led1", "DISPOSITIVO_NO_EXISTE", 1),
        ("SI led1 == ENCENDIDO ENTONCES ENCENDER alarma1", "OPERACION_INCOMPATIBLE", 31),
        ('ENVIAR CORREO A "no-es-correo" MENSAJE "x"', "CORREO_INVALIDO", 1),
        ('ENVIAR CORREO A "a@b.com" MENSAJE ""', "CORREO_INVALIDO", 1),
        ('NOTIFICAR ""', "MENSAJE_VACIO", 1),
        ("REPETIR 0 VECES ENCENDER led1", "REPETICION_INVALIDA", 1),
        ("REPETIR 3 VECES ENCENDER alarma1", "OPERACION_INCOMPATIBLE", 17),
    ],
)
def test_instrucciones_invalidas(
    repositorio: DispositivoRepositoryMemoria, fuente: str, codigo: str, columna: int
) -> None:
    """Las instrucciones inválidas no producen diccionario y señalan el nodo."""
    instrucciones, errores = analizar_texto(fuente, repositorio)
    assert instrucciones == []
    assert len(errores) == 1
    assert (errores[0].codigo, errores[0].linea, errores[0].columna) == (codigo, 1, columna)
    assert errores[0].mensaje


def test_acumula_errores_y_conserva_solo_instrucciones_validas(
    repositorio: DispositivoRepositoryMemoria,
) -> None:
    """Las líneas válidas se conservan entre dos errores semánticos."""
    instrucciones, errores = analizar_texto(
        "ENCENDER led1\nENCENDER dispositivo99\nLISTAR DISPOSITIVOS\nACTIVAR led1",
        repositorio,
    )
    assert instrucciones == [
        {"tipo": "CONTROL_DISPOSITIVO", "operacion": "ENCENDER", "dispositivo": "led1"},
        {"tipo": "LISTADO"},
    ]
    assert [(e.codigo, e.linea, e.columna) for e in errores] == [
        ("DISPOSITIVO_NO_EXISTE", 2, 1), ("OPERACION_INCOMPATIBLE", 4, 1)
    ]


@pytest.mark.parametrize(
    ("fuente", "codigos"),
    [
        ("SI dispositivo99 == ENCENDIDO ENTONCES ENCENDER alarma1",
         ["DISPOSITIVO_NO_EXISTE", "OPERACION_INCOMPATIBLE"]),
        ("REPETIR 0 VECES ENCENDER alarma1",
         ["REPETICION_INVALIDA", "OPERACION_INCOMPATIBLE"]),
    ],
)
def test_valida_accion_aun_si_falla_nodo_exterior(
    repositorio: DispositivoRepositoryMemoria, fuente: str, codigos: list[str]
) -> None:
    """Los errores independientes del cuerpo también se reportan."""
    instrucciones, errores = analizar_texto(fuente, repositorio)
    assert instrucciones == []
    assert [error.codigo for error in errores] == codigos


def test_analisis_no_modifica_repositorio(repositorio: DispositivoRepositoryMemoria) -> None:
    """Validar tanto instrucciones válidas como inválidas no cambia símbolos."""
    inicial = repositorio.listar()
    analizar_texto(
        "ENCENDER led1\nSI alarma1 == ENCENDIDO ENTONCES APAGAR led1\n"
        "REPETIR 2 VECES DESACTIVAR alarma1",
        repositorio,
    )
    assert repositorio.listar() == inicial


def test_analizador_usa_repositorio_inyectado() -> None:
    """No se agregan automáticamente los dispositivos predeterminados."""
    instrucciones, errores = analizar_texto("ENCENDER led1", DispositivoRepositoryMemoria())
    assert instrucciones == []
    assert [error.codigo for error in errores] == ["DISPOSITIVO_NO_EXISTE"]


def test_analizador_no_acumula_resultados_entre_analisis(
    repositorio: DispositivoRepositoryMemoria,
) -> None:
    """Reutilizar un analizador no altera el resultado de una llamada anterior."""
    analizador = Analizador(repositorio)
    primero = analizar_fuente("ENCENDER desconocido").programa
    segundo = analizar_fuente("LISTAR DISPOSITIVOS").programa
    instrucciones_anteriores, errores_anteriores = analizador.analizar(primero)
    instrucciones, errores = analizador.analizar(segundo)
    assert instrucciones == [{"tipo": "LISTADO"}]
    assert errores == []
    assert instrucciones_anteriores == []
    assert [error.codigo for error in errores_anteriores] == ["DISPOSITIVO_NO_EXISTE"]


def test_error_semantico_formato_e_inmutabilidad() -> None:
    """Los errores conservan su información y representación legible."""
    error = ErrorSemantico("CORREO_INVALIDO", "Correo inválido", 2, 3)
    assert str(error) == "Error semántico (línea 2, col 3): Correo inválido"
    with pytest.raises(FrozenInstanceError):
        setattr(error, "linea", 9)


@pytest.mark.parametrize(("veces", "valido"), [(1, True), (100, True), (101, False)])
def test_limite_superior_de_repeticion(
    repositorio: DispositivoRepositoryMemoria, veces: int, valido: bool
) -> None:
    """Se aceptan 1 y 100 repeticiones, pero se rechaza 101."""
    instrucciones, errores = analizar_texto(f"REPETIR {veces} VECES ENCENDER led1", repositorio)
    if valido:
        assert len(instrucciones) == 1
        assert errores == []
    else:
        assert instrucciones == []
        assert len(errores) == 1
        assert errores[0].codigo == "REPETICION_INVALIDA"
        assert "1 y 100" in errores[0].mensaje
