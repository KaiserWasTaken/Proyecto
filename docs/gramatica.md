# Gramática de CommandFlow

Este documento describe los tokens aceptados por el lexer y la gramática
que actualmente analiza el parser. El parser recibe los tokens, no el texto
original; la validez completa exige que **ambas** fases estén libres de errores.

## EBNF

En esta notación, `|` significa alternativa, `{ ... }` repetición cero o más
veces y `[ ... ]` contenido opcional. Las palabras entre comillas son tokens
reservados; `IDENTIFICADOR`, `CADENA`, `NUMERO`, `SALTO_LINEA` y `EOF` son
tipos de token.

```ebnf
programa           = { SALTO_LINEA | instruccion, SALTO_LINEA },
                     [ instruccion ], EOF ;
instruccion        = instruccion_simple | condicional | repetir ;
instruccion_simple = encender | apagar | activar | desactivar | consultar
                   | listar | notificar | enviar_correo ;
encender           = "ENCENDER", IDENTIFICADOR ;
apagar             = "APAGAR", IDENTIFICADOR ;
activar            = "ACTIVAR", IDENTIFICADOR ;
desactivar         = "DESACTIVAR", IDENTIFICADOR ;
consultar          = "CONSULTAR", IDENTIFICADOR ;
listar             = "LISTAR", "DISPOSITIVOS" ;
notificar          = "NOTIFICAR", CADENA ;
enviar_correo      = "ENVIAR", "CORREO", "A", CADENA, "MENSAJE", CADENA ;
condicional        = "SI", IDENTIFICADOR, "==", estado, "ENTONCES",
                     instruccion_simple ;
repetir            = "REPETIR", NUMERO, "VECES", instruccion_simple ;
estado             = "ENCENDIDO" | "APAGADO" | "ACTIVADA" | "DESACTIVADA" ;
```

Se permiten programas vacíos y líneas en blanco; cada instrucción termina en
`SALTO_LINEA` o `EOF`. Los cuerpos de `SI` y `REPETIR` no pueden anidarse.
La propuesta inicial exigía una instrucción: esta versión admite cero y
explicita `EOF`. `IDENTIFICADOR` es el nombre real del token antes llamado `ID`.

## Tokens

Las líneas y columnas son de base 1. El `lexema` conserva el texto original;
el valor es `str` para identificadores y cadenas, `int` para números, y
`None` para los demás tokens.

### Palabras reservadas

| Tipo | Descripción | Ejemplo |
|---|---|---|
| `ENCENDER` | Operación de encendido | `ENCENDER` |
| `APAGAR` | Operación de apagado | `APAGAR` |
| `ACTIVAR` | Operación de activación | `ACTIVAR` |
| `DESACTIVAR` | Operación de desactivación | `DESACTIVAR` |
| `CONSULTAR` | Consulta de dispositivo | `CONSULTAR` |
| `LISTAR` | Inicio de listado | `LISTAR` |
| `DISPOSITIVOS` | Objeto del listado | `DISPOSITIVOS` |
| `NOTIFICAR` | Inicio de notificación | `NOTIFICAR` |
| `ENVIAR` | Inicio de envío | `ENVIAR` |
| `CORREO` | Tipo de envío | `CORREO` |
| `A` | Introduce al destinatario | `A` |
| `MENSAJE` | Introduce el mensaje del correo | `MENSAJE` |
| `SI` | Inicio de condición | `SI` |
| `ENTONCES` | Introduce la acción condicional | `ENTONCES` |
| `REPETIR` | Inicio de repetición | `REPETIR` |
| `VECES` | Separa cantidad y acción | `VECES` |

### Estados reservados

| Tipo | Descripción | Ejemplo |
|---|---|---|
| `ENCENDIDO` | Estado de encendido | `ENCENDIDO` |
| `APAGADO` | Estado de apagado | `APAGADO` |
| `ACTIVADA` | Estado de activación | `ACTIVADA` |
| `DESACTIVADA` | Estado de desactivación | `DESACTIVADA` |

### Otros tokens

| Tipo | Descripción | Ejemplo |
|---|---|---|
| `IDENTIFICADOR` | Nombre ASCII que no es palabra reservada | `led1` |
| `CADENA` | Texto entre comillas dobles | `"Hola"` |
| `NUMERO` | Entero decimal no negativo | `3` |
| `IGUAL_IGUAL` | Comparación de igualdad | `==` |
| `SALTO_LINEA` | Salto LF o CRLF | `\n`, `\r\n` |
| `EOF` | Fin de la secuencia de tokens; lexema vacío | Fin de entrada |

## Decisiones

Las palabras reservadas se reconocen solo en mayúsculas y no pueden utilizarse
como identificadores. Estos distinguen mayúsculas: `LED1` y `led1` son
distintos y siguen el formato `[A-Za-z_][A-Za-z0-9_]*`.

Los comentarios empiezan con `#`; las cadenas admiten `\"`, `\\` y `\n`.
Un escape inválido genera un error y conserva el carácter sin la barra. El
lexer acumula errores y el parser recupera por línea, incluso si hay errores
léxicos. Si cualquiera de las fases tiene errores, el consumidor no debe pasar
a semántica ni a ejecución.

## Ejemplos

Estas entradas son válidas léxica y sintácticamente:

```text
ENCENDER led1
LISTAR DISPOSITIVOS
NOTIFICAR "Prueba"
ENVIAR CORREO A "a@b.com" MENSAJE "Hola"
SI led1 == ENCENDIDO ENTONCES APAGAR led1
```

Cada ejemplo siguiente es una entrada independiente en la línea 1. Se indican
**todos** los errores del lexer y del parser para esa entrada:

| Entrada | Errores esperados: fase, código, línea, columna |
|---|---|
| `ENCENDER led1@` | Léxico: `CARACTER_NO_RECONOCIDO`, 1, 14 |
| `ENCENDER` | Sintáctico: `ESPERABA_IDENTIFICADOR`, 1, 9 |
| `LISTAR led1` | Sintáctico: `ESPERABA_PALABRA`, 1, 8 |
| `encender led1` | Sintáctico: `INSTRUCCION_DESCONOCIDA`, 1, 1 |
| `SI led1 == HOLA ENTONCES APAGAR led1` | Sintáctico: `ESPERABA_ESTADO`, 1, 12 |

En `ENCENDER led1@`, el parser sí produce el nodo de control porque recibe
los tokens válidos; el error léxico sigue haciendo inválida la entrada completa.

## Códigos de error

### Léxicos

| Código | Significado |
|---|---|
| `CARACTER_NO_RECONOCIDO` | Carácter no válido fuera de una cadena o comentario. |
| `CADENA_SIN_CERRAR` | La cadena alcanza un salto o EOF sin comilla de cierre. |
| `IGUAL_SUELTO` | Se encontró `=` sin un segundo `=`. |
| `ESCAPE_INVALIDO` | La secuencia de escape no es `\"`, `\\` ni `\n`. |

### Sintácticos

| Código | Significado |
|---|---|
| `INSTRUCCION_DESCONOCIDA` | Se esperaba una instrucción y el token no inicia una instrucción simple válida. |
| `ESPERABA_IDENTIFICADOR` | Falta un identificador de dispositivo. |
| `ESPERABA_PALABRA` | Falta una palabra reservada requerida por la regla. |
| `ESPERABA_CADENA` | Falta una cadena. |
| `ESPERABA_NUMERO` | Falta el número de repeticiones. |
| `ESPERABA_ESTADO` | Después de `==` no aparece un estado reservado. |
| `ESPERABA_OPERADOR` | Falta el operador `==`. |
| `TOKENS_SOBRANTES` | Hay tokens después de una instrucción completa en la misma línea. |
| `ANIDAMIENTO_NO_PERMITIDO` | El cuerpo de `SI` o `REPETIR` comienza con `SI` o `REPETIR`. |

## Validaciones fuera de la gramática

La gramática no verifica que el dispositivo exista, que su operación o el
estado comparado sean compatibles con su tipo, que el correo tenga un formato
válido, que los mensajes no estén vacíos ni que la repetición esté entre 1 y
100. Estas comprobaciones las realiza el analizador semántico. Por ejemplo,
`ENCENDER alarma1` y `ENCENDER dispositivo99` son sintácticamente válidos,
pero producen errores semánticos.
