"""Pruebas de la tabla de símbolos y el repositorio en memoria."""

from dataclasses import FrozenInstanceError

import pytest

from app.semantic.symbol_table import (
    DispositivoRepository,
    DispositivoRepositoryMemoria,
    ErrorTablaSimbolos,
    Simbolo,
    TablaSimbolos,
)


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


def test_repositorio_inyectado_y_registro() -> None:
    """Una tabla usa los datos existentes del repositorio proporcionado."""
    repositorio: DispositivoRepository = DispositivoRepositoryMemoria()
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


def test_actualizacion_valida_e_invalida() -> None:
    """Una actualización inválida no altera el estado anterior."""
    tabla = TablaSimbolos()
    tabla.actualizar_estado("led1", "ENCENDIDO")
    assert tabla.obtener("led1").estado == "ENCENDIDO"
    with pytest.raises(ErrorTablaSimbolos) as error:
        tabla.actualizar_estado("led1", "ACTIVADA")
    assert error.value.codigo == "ESTADO_INCOMPATIBLE"
    assert tabla.obtener("led1").estado == "ENCENDIDO"


def test_dispositivo_ausente() -> None:
    """Los accesos que requieren un dispositivo rechazan identificadores ausentes."""
    tabla = TablaSimbolos()
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


def test_lecturas_no_modifican_repositorio() -> None:
    """Las listas son independientes y los símbolos no se pueden mutar."""
    tabla = TablaSimbolos()
    simbolo = tabla.obtener("led1")
    instantanea = tabla.listar()
    instantanea.clear()
    with pytest.raises(FrozenInstanceError):
        setattr(simbolo, "estado", "ENCENDIDO")
    assert len(tabla.listar()) == 4
    assert tabla.obtener("led1").estado == "APAGADO"
