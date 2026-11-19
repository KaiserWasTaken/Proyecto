# Análisis semántico

El analizador valida el AST sin ejecutar instrucciones ni modificar estados.
Usa una tabla de símbolos sobre un repositorio inyectado. Los identificadores
distinguen mayúsculas y minúsculas.

## Tabla de símbolos

| Tipo | Estados válidos | Operaciones |
|---|---|---|
| LED | `ENCENDIDO`, `APAGADO` | `ENCENDER`, `APAGAR`, `CONSULTAR` |
| VENTILADOR | `ENCENDIDO`, `APAGADO` | `ENCENDER`, `APAGAR`, `CONSULTAR` |
| ALARMA | `ACTIVADA`, `DESACTIVADA` | `ACTIVAR`, `DESACTIVAR`, `CONSULTAR` |

Los dispositivos iniciales son `led1` APAGADO, `led2` ENCENDIDO,
`alarma1` ACTIVADA y `ventilador1` APAGADO.

`REPETIR` acepta de 1 a 100 veces, ambos límites incluidos.

## Acciones semánticas

| Acción | Comprobación o resultado |
|---|---|
| `verificar_dispositivo` | Existencia en la tabla. |
| `verificar_operacion` | Operación permitida para el dispositivo. |
| `verificar_estado` | Estado válido para el tipo del dispositivo. |
| `verificar_mensaje` | Mensaje no vacío. |
| `verificar_correo` | Formato del destinatario y mensaje no vacío. |
| `verificar_repeticion` | Número de repeticiones entre 1 y 100. |
| `construir_instruccion` | Diccionario de una instrucción previamente validada. |

`construir_instruccion` produce estas estructuras; la acción anidada también
es una instrucción estructurada:

```text
{"tipo":"CONTROL_DISPOSITIVO","operacion":"ENCENDER","dispositivo":"led1"}
{"tipo":"CONSULTA","dispositivo":"led1"}
{"tipo":"LISTADO"}
{"tipo":"NOTIFICACION","mensaje":"Prueba"}
{"tipo":"CORREO","destinatario":"a@b.com","mensaje":"Hola"}
{"tipo":"CONDICIONAL","dispositivo":"led1","estado":"ENCENDIDO","accion":{"tipo":"CONSULTA","dispositivo":"led1"}}
{"tipo":"REPETIR","veces":3,"accion":{"tipo":"CONSULTA","dispositivo":"led1"}}
```

## Errores semánticos

Cada error incluye código, mensaje, línea y columna del nodo.

| Código | Significado |
|---|---|
| `DISPOSITIVO_NO_EXISTE` | Identificador no registrado. |
| `OPERACION_INCOMPATIBLE` | Operación no permitida para el dispositivo. |
| `ESTADO_INCOMPATIBLE` | Estado comparado inválido para el tipo. |
| `MENSAJE_VACIO` | Notificación sin contenido. |
| `CORREO_INVALIDO` | Destinatario inválido o mensaje de correo vacío. |
| `REPETICION_INVALIDA` | Número de repeticiones fuera del rango 1–100. |
