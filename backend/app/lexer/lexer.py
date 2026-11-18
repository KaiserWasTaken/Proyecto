"""Analizador léxico manual para el lenguaje de CommandFlow."""

from app.lexer.errors import ErrorLexico
from app.lexer.tokens import TipoToken, Token


PALABRAS_RESERVADAS: dict[str, TipoToken] = {
    tipo.value: tipo
    for tipo in (
        TipoToken.ENCENDER,
        TipoToken.APAGAR,
        TipoToken.ACTIVAR,
        TipoToken.DESACTIVAR,
        TipoToken.CONSULTAR,
        TipoToken.LISTAR,
        TipoToken.DISPOSITIVOS,
        TipoToken.NOTIFICAR,
        TipoToken.ENVIAR,
        TipoToken.CORREO,
        TipoToken.A,
        TipoToken.MENSAJE,
        TipoToken.SI,
        TipoToken.ENTONCES,
        TipoToken.REPETIR,
        TipoToken.VECES,
        TipoToken.ENCENDIDO,
        TipoToken.APAGADO,
        TipoToken.ACTIVADA,
        TipoToken.DESACTIVADA,
    )
}


def _es_letra(caracter: str) -> bool:
    """Reconoce letras ASCII y el guion bajo."""
    return bool(caracter) and ("A" <= caracter <= "Z" or "a" <= caracter <= "z" or caracter == "_")


def _es_digito(caracter: str) -> bool:
    """Reconoce exclusivamente dígitos ASCII."""
    return bool(caracter) and "0" <= caracter <= "9"


class Lexer:
    """Convierte una fuente en tokens y acumula diagnósticos léxicos."""

    def __init__(self, fuente: str) -> None:
        """Guarda el texto que se analizará."""
        self.fuente = fuente
        self._indice = 0
        self._linea = 1
        self._columna = 1
        self._tokens: list[Token] = []
        self._errores: list[ErrorLexico] = []

    def tokenizar(self) -> tuple[list[Token], list[ErrorLexico]]:
        """Analiza la fuente desde el inicio y devuelve tokens y errores."""
        self._indice = 0
        self._linea = 1
        self._columna = 1
        self._tokens = []
        self._errores = []

        while self._actual():
            caracter = self._actual()
            if caracter in (" ", "\t"):
                self._avanzar()
            elif self._es_salto():
                self._salto_linea()
            elif caracter == "#":
                self._comentario()
            elif _es_letra(caracter):
                self._palabra()
            elif _es_digito(caracter):
                self._numero()
            elif caracter == '"':
                self._cadena()
            elif caracter == "=":
                self._igual()
            else:
                self._errores.append(ErrorLexico(
                    "CARACTER_NO_RECONOCIDO",
                    f"Carácter '{caracter}' no reconocido",
                    self._linea,
                    self._columna,
                ))
                self._avanzar()

        self._tokens.append(Token(TipoToken.EOF, "", None, self._linea, self._columna))
        return self._tokens, self._errores

    def _actual(self) -> str:
        """Devuelve el carácter actual o una cadena vacía al final."""
        if self._indice >= len(self.fuente):
            return ""
        return self.fuente[self._indice]

    def _es_salto(self) -> bool:
        """Reconoce un salto LF o CRLF sin consumirlo."""
        return self._actual() == "\n" or self.fuente.startswith("\r\n", self._indice)

    def _avanzar(self) -> str:
        """Consume un carácter que no forma parte de un salto de línea."""
        caracter = self.fuente[self._indice]
        self._indice += 1
        self._columna += 1
        return caracter

    def _salto_linea(self) -> None:
        """Emite un único token por salto LF o CRLF."""
        longitud = 2 if self.fuente.startswith("\r\n", self._indice) else 1
        lexema = self.fuente[self._indice:self._indice + longitud]
        self._tokens.append(Token(TipoToken.SALTO_LINEA, lexema, None, self._linea, self._columna))
        self._indice += longitud
        self._linea += 1
        self._columna = 1

    def _comentario(self) -> None:
        """Omite el comentario sin consumir su salto de línea."""
        while self._actual() and not self._es_salto():
            self._avanzar()

    def _palabra(self) -> None:
        """Reconoce un identificador ASCII o una palabra reservada exacta."""
        inicio, linea, columna = self._indice, self._linea, self._columna
        while _es_letra(self._actual()) or _es_digito(self._actual()):
            self._avanzar()
        lexema = self.fuente[inicio:self._indice]
        tipo = PALABRAS_RESERVADAS.get(lexema, TipoToken.IDENTIFICADOR)
        valor = lexema if tipo == TipoToken.IDENTIFICADOR else None
        self._tokens.append(Token(tipo, lexema, valor, linea, columna))

    def _numero(self) -> None:
        """Reconoce un entero no negativo en notación decimal ASCII."""
        inicio, linea, columna = self._indice, self._linea, self._columna
        while _es_digito(self._actual()):
            self._avanzar()
        lexema = self.fuente[inicio:self._indice]
        # Una letra contigua inicia otro token; el parser decide si es válida.
        valor = 0
        for posicion in range(0, len(lexema), 9):
            bloque = lexema[posicion:posicion + 9]
            valor = valor * (10 ** len(bloque)) + int(bloque)
        self._tokens.append(Token(TipoToken.NUMERO, lexema, valor, linea, columna))

    def _cadena(self) -> None:
        """Interpreta escapes y recupera cadenas sin cerrar al final de línea."""
        inicio, linea, columna = self._indice, self._linea, self._columna
        self._avanzar()
        contenido: list[str] = []
        escapes = {'"': '"', "\\": "\\", "n": "\n"}
        while self._actual() and not self._es_salto():
            if self._actual() == '"':
                self._avanzar()
                lexema = self.fuente[inicio:self._indice]
                self._tokens.append(Token(TipoToken.CADENA, lexema, "".join(contenido), linea, columna))
                return
            if self._actual() != "\\":
                contenido.append(self._avanzar())
                continue
            linea_escape, columna_escape = self._linea, self._columna
            self._avanzar()
            if not self._actual() or self._es_salto():
                break
            caracter = self._avanzar()
            if caracter not in escapes:
                self._errores.append(ErrorLexico(
                    "ESCAPE_INVALIDO",
                    f"Secuencia de escape '\\{caracter}' no válida",
                    linea_escape,
                    columna_escape,
                ))
                contenido.append(caracter)
            else:
                contenido.append(escapes[caracter])
        self._errores.append(ErrorLexico("CADENA_SIN_CERRAR", "Cadena sin cerrar", linea, columna))

    def _igual(self) -> None:
        """Reconoce == o informa de un signo igual aislado."""
        linea, columna = self._linea, self._columna
        self._avanzar()
        if self._actual() == "=":
            self._avanzar()
            self._tokens.append(Token(TipoToken.IGUAL_IGUAL, "==", None, linea, columna))
        else:
            self._errores.append(ErrorLexico("IGUAL_SUELTO", "Signo '=' sin pareja", linea, columna))
