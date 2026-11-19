# Base de datos

SQLAlchemy define únicamente estas tablas:

| Tabla | Columnas |
|---|---|
| `dispositivos` | `identificador` (PK), `tipo`, `estado` |
| `notificaciones` | `id` (PK autoincremental), `mensaje`, `creada_en` |
| `ejecuciones` | `id` (PK autoincremental), `fuente`, `exito`, `eventos` (JSON), `creada_en` |

```text
dispositivos         notificaciones          ejecuciones
-------------        --------------          -----------
identificador PK     id PK                   id PK
tipo                 mensaje                 fuente
estado               creada_en               exito
                                             eventos JSON
                                             creada_en
```

Las tablas no tienen claves foráneas entre sí. Las notificaciones se listan
en orden de registro; `listar_ultimas(n)` devuelve las ejecuciones más
recientes primero.

## Inicialización

`init_db(engine)` crea las tablas si no existen y carga los cuatro
dispositivos iniciales solo cuando `dispositivos` está vacía. Repetirla no
duplica dispositivos ni restablece estados. `DATABASE_URL` configura el motor;
el driver de PostgreSQL es psycopg 3.
Al arrancar, la aplicación reintenta hasta cinco veces los errores de conexión,
con dos segundos entre intentos; si persisten, el arranque falla.

## Transacciones

Los repositorios reciben una `Session` y hacen `flush` para enviar sus cambios,
pero no hacen `commit` ni `rollback`. La capa que orquesta la ejecución decide
confirmar o revertir la transacción completa: por ejemplo, puede revertir
juntos los cambios de dispositivo y las notificaciones al abortar una
ejecución. `init_db`, por separado, confirma su propia carga inicial.

Las pruebas rápidas usan SQLite en memoria; las marcadas `postgres` se ejecutan
solo si `DATABASE_URL` apunta a PostgreSQL y requieren las tablas inicializadas.
