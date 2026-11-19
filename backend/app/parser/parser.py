"""Parser de descenso recursivo con recuperación por línea."""

from typing import NoReturn

from app.ast.nodes import (
    Condicional,
    Consultar,
    ControlDispositivo,
    EnviarCorreo,
    Instruccion,
    InstruccionSimple,
    Listar,
    Notificar,
    Operacion,
    Programa,
    Repetir,
)
from app.lexer.tokens import TipoToken, Token
from app.parser.errors import ErrorSintactico


_OPERACIONES: dict[TipoToken, Operacion] = {
    TipoToken.ENCENDER: Operacion.ENCENDER,
    TipoToken.APAGAR: Operacion.APAGAR,
    TipoToken.ACTIVAR: Operacion.ACTIVAR,
    TipoToken.DESACTIVAR: Operacion.DESACTIVAR,
}
_ESTADOS = {
    TipoToken.ENCENDIDO,
    TipoToken.APAGADO,
    TipoToken.ACTIVADA,
    TipoToken.DESACTIVADA,
}


class _FalloSintactico(Exception):
    """Interrumpe el análisis de una línea y transporta su diagnóstico."""

    def __init__(self, error: ErrorSintactico) -> None:
        """Guarda el diagnóstico para la recuperación del programa."""
        self.error = error
        super().__init__(str(error))


class Parser:
    """Analiza los tokens de un programa sin realizar validaciones semánticas."""

    def __init__(self, tokens: list[Token]) -> None:
        """Recibe una secuencia terminada en EOF, como la producida por el lexer."""
        if not tokens or tokens[-1].tipo != TipoToken.EOF:
            raise ValueError("La lista de tokens debe terminar en EOF")
        if any(token.tipo == TipoToken.EOF for token in tokens[:-1]):
            raise ValueError("EOF solo puede aparecer al final de la lista de tokens")
        self._tokens = tuple(tokens)
        self._indice = 0
        self._errores: list[ErrorSintactico] = []

    def parsear(self) -> tuple[Programa, list[ErrorSintactico]]:
        """Devuelve el AST de las líneas válidas y los errores sintácticos."""
        self._indice = 0
        self._errores = []
        programa = self._programa()
        return programa, self._errores

    def _actual(self) -> Token:
        """Devuelve el token en la posición actual."""
        return self._tokens[self._indice]

    def _avanzar(self) -> Token:
        """Consume un token distinto de EOF y devuelve el token actual."""
        token = self._actual()
        if token.tipo != TipoToken.EOF:
            self._indice += 1
        return token

    def _fallar(self, codigo: str, esperado: str) -> NoReturn:
        """Genera un diagnóstico para el token encontrado."""
        token = self._actual()
        if token.tipo in (TipoToken.SALTO_LINEA, TipoToken.EOF):
            encontrado = "fin de línea"
        else:
            encontrado = repr(token.lexema)
        raise _FalloSintactico(ErrorSintactico(
            codigo,
            f"{esperado}, pero se encontró {encontrado}",
            token.linea,
            token.columna,
        ))

    def _esperar(self, tipo: TipoToken, codigo: str, esperado: str) -> Token:
        """Consume el tipo esperado o informa el token encontrado."""
        if self._actual().tipo != tipo:
            self._fallar(codigo, esperado)
        return self._avanzar()

    @staticmethod
    def _valor_texto(token: Token) -> str:
        """Obtiene el valor textual de un token producido correctamente."""
        if not isinstance(token.valor, str):
            raise ValueError(f"El token {token.tipo} debe contener un valor de texto")
        return token.valor

    @staticmethod
    def _valor_numero(token: Token) -> int:
        """Obtiene el valor entero de un token producido correctamente."""
        if type(token.valor) is not int:
            raise ValueError("El token NUMERO debe contener un valor entero")
        return token.valor

    def _programa(self) -> Programa:
        """Analiza instrucciones separadas por saltos de línea."""
        instrucciones: list[Instruccion] = []
        while self._actual().tipo != TipoToken.EOF:
            # Cada iteración consume un salto o una línea completa hasta salto/EOF.
            if self._actual().tipo == TipoToken.SALTO_LINEA:
                self._avanzar()
                continue
            try:
                instruccion = self._instruccion()
                if self._actual().tipo not in (TipoToken.SALTO_LINEA, TipoToken.EOF):
                    self._fallar("TOKENS_SOBRANTES", "Se esperaba fin de línea")
                instrucciones.append(instruccion)
            except _FalloSintactico as fallo:
                self._errores.append(fallo.error)
                while self._actual().tipo not in (TipoToken.SALTO_LINEA, TipoToken.EOF):
                    self._avanzar()
            if self._actual().tipo == TipoToken.SALTO_LINEA:
                self._avanzar()
        return Programa(1, 1, tuple(instrucciones))

    def _instruccion(self) -> Instruccion:
        """Analiza una instrucción simple, condicional o repetición."""
        if self._actual().tipo == TipoToken.SI:
            return self._condicional()
        if self._actual().tipo == TipoToken.REPETIR:
            return self._repetir()
        return self._instruccion_simple()

    def _instruccion_simple(self) -> InstruccionSimple:
        """Analiza una instrucción simple y rechaza el anidamiento."""
        tipo = self._actual().tipo
        if tipo in (TipoToken.SI, TipoToken.REPETIR):
            self._fallar("ANIDAMIENTO_NO_PERMITIDO", "Se esperaba una instrucción simple sin anidamiento")
        if tipo in _OPERACIONES:
            return self._control_dispositivo(_OPERACIONES[tipo])
        if tipo == TipoToken.CONSULTAR:
            return self._consultar()
        if tipo == TipoToken.LISTAR:
            return self._listar()
        if tipo == TipoToken.NOTIFICAR:
            return self._notificar()
        if tipo == TipoToken.ENVIAR:
            return self._enviar_correo()
        self._fallar("INSTRUCCION_DESCONOCIDA", "Se esperaba una instrucción")

    def _control_dispositivo(self, operacion: Operacion) -> ControlDispositivo:
        """Analiza una operación de control y su identificador."""
        inicio = self._avanzar()
        dispositivo = self._esperar(
            TipoToken.IDENTIFICADOR,
            "ESPERABA_IDENTIFICADOR",
            f"Se esperaba un identificador de dispositivo después de {operacion.value}",
        )
        return ControlDispositivo(inicio.linea, inicio.columna, operacion, self._valor_texto(dispositivo))

    def _consultar(self) -> Consultar:
        """Analiza una consulta de dispositivo."""
        inicio = self._avanzar()
        dispositivo = self._esperar(
            TipoToken.IDENTIFICADOR,
            "ESPERABA_IDENTIFICADOR",
            "Se esperaba un identificador de dispositivo después de CONSULTAR",
        )
        return Consultar(inicio.linea, inicio.columna, self._valor_texto(dispositivo))

    def _listar(self) -> Listar:
        """Analiza el listado de dispositivos."""
        inicio = self._avanzar()
        self._esperar(TipoToken.DISPOSITIVOS, "ESPERABA_PALABRA", "Se esperaba DISPOSITIVOS después de LISTAR")
        return Listar(inicio.linea, inicio.columna)

    def _notificar(self) -> Notificar:
        """Analiza una notificación con mensaje de cadena."""
        inicio = self._avanzar()
        mensaje = self._esperar(TipoToken.CADENA, "ESPERABA_CADENA", "Se esperaba una cadena después de NOTIFICAR")
        return Notificar(inicio.linea, inicio.columna, self._valor_texto(mensaje))

    def _enviar_correo(self) -> EnviarCorreo:
        """Analiza destinatario y mensaje de un envío de correo."""
        inicio = self._avanzar()
        self._esperar(TipoToken.CORREO, "ESPERABA_PALABRA", "Se esperaba CORREO después de ENVIAR")
        self._esperar(TipoToken.A, "ESPERABA_PALABRA", "Se esperaba A después de CORREO")
        destinatario = self._esperar(TipoToken.CADENA, "ESPERABA_CADENA", "Se esperaba una cadena después de A")
        self._esperar(TipoToken.MENSAJE, "ESPERABA_PALABRA", "Se esperaba MENSAJE después del destinatario")
        mensaje = self._esperar(TipoToken.CADENA, "ESPERABA_CADENA", "Se esperaba una cadena después de MENSAJE")
        return EnviarCorreo(
            inicio.linea, inicio.columna, self._valor_texto(destinatario), self._valor_texto(mensaje)
        )

    def _condicional(self) -> Condicional:
        """Analiza una comparación de estado y una acción simple."""
        inicio = self._avanzar()
        dispositivo = self._esperar(
            TipoToken.IDENTIFICADOR, "ESPERABA_IDENTIFICADOR",
            "Se esperaba un identificador de dispositivo después de SI",
        )
        self._esperar(TipoToken.IGUAL_IGUAL, "ESPERABA_OPERADOR", "Se esperaba == después del dispositivo")
        if self._actual().tipo not in _ESTADOS:
            self._fallar("ESPERABA_ESTADO", "Se esperaba un estado después de ==")
        estado = self._avanzar()
        self._esperar(TipoToken.ENTONCES, "ESPERABA_PALABRA", "Se esperaba ENTONCES después del estado")
        accion = self._instruccion_simple()
        return Condicional(inicio.linea, inicio.columna, self._valor_texto(dispositivo), estado.lexema, accion)

    def _repetir(self) -> Repetir:
        """Analiza una cantidad y una acción simple para repetir."""
        inicio = self._avanzar()
        veces = self._esperar(TipoToken.NUMERO, "ESPERABA_NUMERO", "Se esperaba un número después de REPETIR")
        self._esperar(TipoToken.VECES, "ESPERABA_PALABRA", "Se esperaba VECES después del número")
        accion = self._instruccion_simple()
        return Repetir(inicio.linea, inicio.columna, self._valor_numero(veces), accion)
