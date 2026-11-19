"""Pruebas de la tabla de símbolos y el repositorio en memoria."""

from dataclasses import FrozenInstanceError
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base
from app.db.repositorios import PostgresDispositivoRepository
from app.semantic.symbol_table import (
    DispositivoRepository,
    DispositivoRepositoryMemoria,
    ErrorTablaSimbolos,
    Simbolo,
    TablaSimbolos,
)


@pytest.fixture(params=["memoria", "sqlite"])
def repositorio_contrato(request: pytest.FixtureRequest) -> Iterator[DispositivoRepository]:
    """Ejecuta el mismo contrato con repositorios inicialmente vacíos."""
    if request.param == "memoria":
        yield DispositivoRepositoryMemoria()
    else:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as sesion:
            yield PostgresDispositivoRepository(sesion)
        engine.dispose()


@pytest.fixture
def tabla_contrato(repositorio_contrato: DispositivoRepository) -> TablaSimbolos:
    """Carga los dispositivos iniciales en el repositorio parametrizado."""
    for simbolo in TablaSimbolos().listar():
        repositorio_contrato.registrar(simbolo)
    return TablaSimbolos(repositorio_contrato)


def test_carga_inicial_y_catalogo() -> None:
    """El catálogo inicial conserva los tipos, estados y operaciones solicitados."""
    tabla = TablaSimbolos()
    assert [(s.identificador, s.tipo, s.estado) for s in tabla.listar()] == [
        ("led1", "LED", "APAGADO"),
        ("led2", "LED", "ENCENDIDO"),
        ("alarma1", "ALARMA", "ACTIVADA"),
        ("ventilador1", "VENTILADOR", "APAGADO"),
    ]
    assert tabla.obtener("alarma1").operaciones_permitidas == {
        "ACTIVAR", "DESACTIVAR", "CONSULTAR"
    }
    assert tabla.operacion_permitida("led1", "ENCENDER")
    assert not tabla.operacion_permitida("led1", "ACTIVAR")
    assert tabla.estado_valido_para_tipo("VENTILADOR", "ENCENDIDO")
    assert not tabla.estado_valido_para_tipo("ALARMA", "ENCENDIDO")


def test_repositorio_inyectado_y_registro(repositorio_contrato: DispositivoRepository) -> None:
    """Una tabla usa los datos existentes del repositorio proporcionado."""
    repositorio = repositorio_contrato
    tabla = TablaSimbolos(repositorio)
    assert tabla.listar() == []
    simbolo = Simbolo("led3", "LED", "APAGADO")
    tabla.registrar(simbolo)
    assert tabla.existe("led3")
    assert repositorio.obtener("led3") == simbolo
    with pytest.raises(ErrorTablaSimbolos) as error:
        tabla.registrar(simbolo)
    assert error.value.codigo == "DISPOSITIVO_DUPLICADO"
    assert tabla.listar() == [simbolo]


def test_actualizacion_valida_e_invalida(tabla_contrato: TablaSimbolos) -> None:
    """Una actualización inválida no altera el estado anterior."""
    tabla = tabla_contrato
    anterior = tabla.obtener("led1")
    tabla.actualizar_estado("led1", "ENCENDIDO")
    actualizado = tabla.obtener("led1")
    assert actualizado is not anterior
    assert anterior.estado == "APAGADO"
    assert actualizado.estado == "ENCENDIDO"
    with pytest.raises(ErrorTablaSimbolos) as error:
        tabla.actualizar_estado("led1", "ACTIVADA")
    assert error.value.codigo == "ESTADO_INCOMPATIBLE"
    assert tabla.obtener("led1").estado == "ENCENDIDO"


def test_repositorio_valida_actualizacion_directa(
    repositorio_contrato: DispositivoRepository,
) -> None:
    """Ambos repositorios validan estados y dispositivos sin pasar por la tabla."""
    repositorio_contrato.registrar(Simbolo("alarma1", "ALARMA", "ACTIVADA"))
    anterior = repositorio_contrato.obtener("alarma1")
    with pytest.raises(ErrorTablaSimbolos) as error:
        repositorio_contrato.actualizar_estado("alarma1", "ENCENDIDO")
    assert error.value.codigo == "ESTADO_INCOMPATIBLE"
    assert repositorio_contrato.obtener("alarma1") == anterior
    with pytest.raises(ErrorTablaSimbolos) as error:
        repositorio_contrato.actualizar_estado("inexistente", "APAGADO")
    assert error.value.codigo == "DISPOSITIVO_NO_EXISTE"
    repositorio_contrato.actualizar_estado("alarma1", "DESACTIVADA")
    assert anterior == Simbolo("alarma1", "ALARMA", "ACTIVADA")
    assert repositorio_contrato.obtener("alarma1") == Simbolo("alarma1", "ALARMA", "DESACTIVADA")


def test_identificadores_distinguen_mayusculas(tabla_contrato: TablaSimbolos) -> None:
    """Registro, búsqueda y actualización usan identificadores exactos."""
    tabla = tabla_contrato
    assert not tabla.existe("LED1")
    with pytest.raises(ErrorTablaSimbolos) as error:
        tabla.obtener("LED1")
    assert error.value.codigo == "DISPOSITIVO_NO_EXISTE"
    tabla.registrar(Simbolo("LED1", "LED", "APAGADO"))
    assert tabla.existe("led1")
    assert tabla.existe("LED1")
    tabla.actualizar_estado("LED1", "ENCENDIDO")
    assert tabla.obtener("LED1").estado == "ENCENDIDO"
    assert tabla.obtener("led1").estado == "APAGADO"
    with pytest.raises(ErrorTablaSimbolos) as error:
        tabla.registrar(Simbolo("LED1", "LED", "ENCENDIDO"))
    assert error.value.codigo == "DISPOSITIVO_DUPLICADO"


def test_dispositivo_ausente(tabla_contrato: TablaSimbolos) -> None:
    """Los accesos que requieren un dispositivo rechazan identificadores ausentes."""
    tabla = tabla_contrato
    assert not tabla.existe("desconocido")
    for operacion in (
        lambda: tabla.obtener("desconocido"),
        lambda: tabla.operacion_permitida("desconocido", "ENCENDER"),
        lambda: tabla.actualizar_estado("desconocido", "APAGADO"),
    ):
        with pytest.raises(ErrorTablaSimbolos) as error:
            operacion()
        assert error.value.codigo == "DISPOSITIVO_NO_EXISTE"


def test_simbolos_y_catalogo_no_admiten_datos_invalidos() -> None:
    """Se rechazan identificadores, tipos y estados inválidos."""
    for argumentos, codigo in (
        (("", "LED", "APAGADO"), "IDENTIFICADOR_INVALIDO"),
        (("otro", "DESCONOCIDO", "APAGADO"), "TIPO_NO_EXISTE"),
        (("otro", "ALARMA", "ENCENDIDO"), "ESTADO_INCOMPATIBLE"),
    ):
        with pytest.raises(ErrorTablaSimbolos) as error:
            Simbolo(*argumentos)
        assert error.value.codigo == codigo
    with pytest.raises(ErrorTablaSimbolos) as error:
        TablaSimbolos().estado_valido_para_tipo("DESCONOCIDO", "APAGADO")
    assert error.value.codigo == "TIPO_NO_EXISTE"


def test_lecturas_no_modifican_repositorio(tabla_contrato: TablaSimbolos) -> None:
    """Las listas son independientes y los símbolos no se pueden mutar."""
    tabla = tabla_contrato
    simbolo = tabla.obtener("led1")
    instantanea = tabla.listar()
    instantanea.clear()
    with pytest.raises(FrozenInstanceError):
        setattr(simbolo, "estado", "ENCENDIDO")
    assert len(tabla.listar()) == 4
    assert tabla.obtener("led1").estado == "APAGADO"
