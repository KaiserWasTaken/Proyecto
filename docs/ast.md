# Árbol de sintaxis abstracta

El AST está definido en [nodes.py](../backend/app/ast/nodes.py) y no depende del lexer,
parser ni de la tabla de símbolos. Los nodos son dataclasses inmutables y
heredan de `Nodo`, con `linea` y `columna` de base 1. El parser sitúa cada
instrucción en su primer token; para `Programa` usa siempre línea 1, columna 1.

## Nodos

La tabla muestra los atributos específicos; todos incluyen también `linea` y
`columna`.

| Nodo | Atributos | Significado |
|---|---|---|
| `Programa` | `instrucciones: tuple[Instruccion, ...]` | Instrucciones del programa; una tupla vacía representa un programa vacío. |
| `ControlDispositivo` | `operacion: Operacion`, `dispositivo: str` | Operación de control sobre un identificador. |
| `Consultar` | `dispositivo: str` | Consulta de un dispositivo. |
| `Listar` | Ninguno | Listado de dispositivos. |
| `Notificar` | `mensaje: str` | Mensaje de notificación. |
| `EnviarCorreo` | `destinatario: str`, `mensaje: str` | Destinatario y contenido del correo. |
| `Condicional` | `dispositivo: str`, `estado: str`, `accion: InstruccionSimple` | Comparación de estado y acción condicionada. |
| `Repetir` | `veces: int`, `accion: InstruccionSimple` | Cantidad de repeticiones y acción. |

`Operacion` contiene `ENCENDER`, `APAGAR`, `ACTIVAR` y `DESACTIVAR`.
`InstruccionSimple` es la unión de `ControlDispositivo`, `Consultar`,
`Listar`, `Notificar` y `EnviarCorreo`; `Instruccion` añade `Condicional`
y `Repetir`.

## Ejemplo de árbol

Para `SI led1 == ENCENDIDO ENTONCES APAGAR led1`:

```text
Programa (línea 1, columna 1)
└── Condicional (línea 1, columna 1)
    ├── dispositivo: "led1"
    ├── estado: "ENCENDIDO"
    └── accion: ControlDispositivo (línea 1, columna 31)
        ├── operacion: APAGAR
        └── dispositivo: "led1"
```

`programa.to_dict()` devuelve una estructura serializable con `json.dumps`:

```json
{
  "tipo": "Programa",
  "linea": 1,
  "columna": 1,
  "instrucciones": [
    {
      "tipo": "Condicional",
      "linea": 1,
      "columna": 1,
      "dispositivo": "led1",
      "estado": "ENCENDIDO",
      "accion": {
        "tipo": "ControlDispositivo",
        "linea": 1,
        "columna": 31,
        "operacion": "APAGAR",
        "dispositivo": "led1"
      }
    }
  ]
}
```

`NodoVisitor[T]` declara un método `visit_*` por nodo. Cada nodo usa
`accept(visitor)` para despachar al método correspondiente; el visitante
decide cómo recorrer los hijos.
