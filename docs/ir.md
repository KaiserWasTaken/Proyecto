# Representación intermedia

El generador recibe instrucciones semánticas válidas y produce una lista de
`InstruccionIR` con índices absolutos. Cada programa termina en `HALT`.

| Operación | Significado |
|---|---|
| `GET_STATE d` | Lee el estado de `d` y genera un evento de consulta. |
| `SET_STATE d estado` | Actualiza el estado de `d`. |
| `COMPARE d == estado` | Compara el estado actual y guarda el resultado booleano. |
| `JUMP_IF_FALSE n` | Salta al índice absoluto `n` si la comparación es falsa. |
| `NOTIFY mensaje` | Registra una notificación. |
| `SEND_EMAIL destinatario mensaje` | Envía un correo por el puerto correspondiente. |
| `LIST_DEVICES` | Genera un listado de los dispositivos. |
| `HALT` | Finaliza la ejecución. |

`LIST_DEVICES` se añade a las siete instrucciones originales porque `GET_STATE`
consulta un dispositivo individual y no representa el listado completo.

## Traducción

| Comando | IR |
|---|---|
| `ENCENDER d` / `APAGAR d` | `SET_STATE d ENCENDIDO` / `SET_STATE d APAGADO` |
| `ACTIVAR d` / `DESACTIVAR d` | `SET_STATE d ACTIVADA` / `SET_STATE d DESACTIVADA` |
| `CONSULTAR d` | `GET_STATE d` |
| `LISTAR DISPOSITIVOS` | `LIST_DEVICES` |
| `NOTIFICAR m` | `NOTIFY m` |
| `ENVIAR CORREO A d MENSAJE m` | `SEND_EMAIL d m` |
| `SI d == estado ENTONCES acción` | `GET_STATE d`, `COMPARE d == estado`, `JUMP_IF_FALSE n`, IR de la acción; `n` apunta después del cuerpo. |
| `REPETIR n VECES acción` | IR de la acción expandido `n` veces; el analizador exige 1–100. |

Ejemplo con un condicional en medio:

```text
ENCENDER led2
SI led1 == ENCENDIDO ENTONCES APAGAR led1
NOTIFICAR "fin"
```

```text
0 SET_STATE led2 ENCENDIDO
1 GET_STATE led1
2 COMPARE led1 == ENCENDIDO
3 JUMP_IF_FALSE 5
4 SET_STATE led1 APAGADO
5 NOTIFY fin
6 HALT
```

El salto apunta a la notificación, inmediatamente después del cuerpo.
