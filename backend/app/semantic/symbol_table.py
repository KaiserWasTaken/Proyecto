"""Tabla de símbolos y repositorio de dispositivos independientes de la API."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Mapping


class ErrorTablaSimbolos(ValueError):
    """Error de catálogo, registro o acceso a un dispositivo."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        """Conserva el código y el mensaje para quien use la tabla."""
        self.codigo = codigo
        self.mensaje = mensaje
        super().__init__(mensaje)


@dataclass(frozen=True)
class TipoDispositivo:
    """Estados y operaciones permitidos para un tipo de dispositivo."""

    estados: frozenset[str]
    operaciones: frozenset[str]


CATALOGO_TIPOS: Mapping[str, TipoDispositivo] = MappingProxyType({
    "LED": TipoDispositivo(
        frozenset({"ENCENDIDO", "APAGADO"}),
        frozenset({"ENCENDER", "APAGAR", "CONSULTAR"}),
    ),
    "VENTILADOR": TipoDispositivo(
        frozenset({"ENCENDIDO", "APAGADO"}),
        frozenset({"ENCENDER", "APAGAR", "CONSULTAR"}),
    ),
    "ALARMA": TipoDispositivo(
        frozenset({"ACTIVADA", "DESACTIVADA"}),
        frozenset({"ACTIVAR", "DESACTIVAR", "CONSULTAR"}),
    ),
})


def _obtener_tipo(tipo: str) -> TipoDispositivo:
    """Devuelve un tipo del catálogo o informa que no existe."""
    if tipo not in CATALOGO_TIPOS:
        raise ErrorTablaSimbolos("TIPO_NO_EXISTE", f"Tipo de dispositivo desconocido: {tipo}")
    return CATALOGO_TIPOS[tipo]


@dataclass(frozen=True)
class Simbolo:
    """Dispositivo inmutable con operaciones derivadas de su tipo."""

    identificador: str
    tipo: str
    estado: str

    def __post_init__(self) -> None:
        """Impide crear símbolos sin identificador o con estados inválidos."""
        if not self.identificador or not self.identificador.strip():
            raise ErrorTablaSimbolos("IDENTIFICADOR_INVALIDO", "El identificador no puede estar vacío")
        if self.estado not in _obtener_tipo(self.tipo).estados:
            raise ErrorTablaSimbolos(
                "ESTADO_INCOMPATIBLE",
                f"El estado {self.estado} no es válido para el tipo {self.tipo}",
            )

    @property
    def operaciones_permitidas(self) -> frozenset[str]:
        """Devuelve las operaciones del tipo del dispositivo."""
        return _obtener_tipo(self.tipo).operaciones


class DispositivoRepository(ABC):
    """Almacena dispositivos con identificadores de comparación exacta.

    Los identificadores distinguen mayúsculas de minúsculas y no se normalizan;
    por ejemplo, ``led1`` y ``LED1`` son distintos en todas las operaciones.
    """

    @abstractmethod
    def registrar(self, simbolo: Simbolo) -> None:
        """Registra un dispositivo nuevo; rechaza identificadores duplicados."""

    @abstractmethod
    def obtener(self, identificador: str) -> Simbolo | None:
        """Obtiene un dispositivo o devuelve None si no existe."""

    @abstractmethod
    def listar(self) -> list[Simbolo]:
        """Devuelve una instantánea de los dispositivos registrados."""

    @abstractmethod
    def actualizar_estado(self, identificador: str, estado: str) -> None:
        """Actualiza el estado de un dispositivo existente."""


class DispositivoRepositoryMemoria(DispositivoRepository):
    """Repositorio en memoria sin dependencias de infraestructura."""

    def __init__(self) -> None:
        """Crea un repositorio inicialmente vacío."""
        self._dispositivos: dict[str, Simbolo] = {}

    def registrar(self, simbolo: Simbolo) -> None:
        """Registra un símbolo sin sobrescribir uno existente."""
        if simbolo.identificador in self._dispositivos:
            raise ErrorTablaSimbolos(
                "DISPOSITIVO_DUPLICADO",
                f"El dispositivo {simbolo.identificador} ya está registrado",
            )
        self._dispositivos[simbolo.identificador] = simbolo

    def obtener(self, identificador: str) -> Simbolo | None:
        """Obtiene un símbolo sin permitir modificarlo desde fuera."""
        return self._dispositivos.get(identificador)

    def listar(self) -> list[Simbolo]:
        """Devuelve una lista independiente con los símbolos registrados."""
        return list(self._dispositivos.values())

    def actualizar_estado(self, identificador: str, estado: str) -> None:
        """Sustituye el símbolo tras validar el estado para su tipo."""
        simbolo = self.obtener(identificador)
        if simbolo is None:
            raise ErrorTablaSimbolos(
                "DISPOSITIVO_NO_EXISTE", f"El dispositivo {identificador} no existe"
            )
        self._dispositivos[identificador] = replace(simbolo, estado=estado)


class TablaSimbolos:
    """Interfaz de consulta y actualización sobre un repositorio inyectable."""

    def __init__(self, repositorio: DispositivoRepository | None = None) -> None:
        """Sin repositorio explícito, crea uno con los dispositivos iniciales."""
        if repositorio is None:
            repositorio = DispositivoRepositoryMemoria()
            for simbolo in (
                Simbolo("led1", "LED", "APAGADO"),
                Simbolo("led2", "LED", "ENCENDIDO"),
                Simbolo("alarma1", "ALARMA", "ACTIVADA"),
                Simbolo("ventilador1", "VENTILADOR", "APAGADO"),
            ):
                repositorio.registrar(simbolo)
        self._repositorio = repositorio

    def registrar(self, simbolo: Simbolo) -> None:
        """Registra un símbolo nuevo en el repositorio."""
        self._repositorio.registrar(simbolo)

    def obtener(self, identificador: str) -> Simbolo:
        """Obtiene un símbolo o informa que el dispositivo no existe."""
        simbolo = self._repositorio.obtener(identificador)
        if simbolo is None:
            raise ErrorTablaSimbolos(
                "DISPOSITIVO_NO_EXISTE", f"El dispositivo {identificador} no existe"
            )
        return simbolo

    def existe(self, identificador: str) -> bool:
        """Indica si el identificador está registrado."""
        return self._repositorio.obtener(identificador) is not None

    def listar(self) -> list[Simbolo]:
        """Devuelve una instantánea de los dispositivos registrados."""
        return self._repositorio.listar()

    def actualizar_estado(self, identificador: str, estado: str) -> None:
        """Valida y actualiza el estado sin ejecutar instrucciones."""
        simbolo = self.obtener(identificador)
        if not self.estado_valido_para_tipo(simbolo.tipo, estado):
            raise ErrorTablaSimbolos(
                "ESTADO_INCOMPATIBLE",
                f"El estado {estado} no es válido para el tipo {simbolo.tipo}",
            )
        self._repositorio.actualizar_estado(identificador, estado)

    def operacion_permitida(self, identificador: str, operacion: str) -> bool:
        """Indica si la operación pertenece al catálogo del dispositivo."""
        return operacion in self.obtener(identificador).operaciones_permitidas

    def estado_valido_para_tipo(self, tipo: str, estado: str) -> bool:
        """Indica si un estado pertenece a un tipo existente del catálogo."""
        return estado in _obtener_tipo(tipo).estados
