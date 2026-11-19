# Ejecutor

`Ejecutor(repositorio, servicio_correo, registro_notificaciones).ejecutar(ir)`
recorre el IR con un puntero explícito. Usa la tabla de símbolos sobre el
repositorio inyectado para consultar y validar estados. `COMPARE` guarda un
booleano para `JUMP_IF_FALSE`; `HALT` termina. Cada llamada comienza con un
registro de comparación independiente.

El resultado contiene `exito`, errores y eventos ordenados. Los eventos de
`SET_STATE` incluyen dispositivo y estado; las consultas y los listados también
recogen los datos leídos. La VM por sí sola no revierte acciones anteriores
al abortar; la capa de aplicación gestiona la transacción. Un máximo de
10 000 instrucciones evita bucles.

## Puertos

- `ServicioCorreo.enviar(destinatario, mensaje)` lanza `ErrorCorreo` si falla.
- `RegistroNotificaciones.registrar(mensaje)` registra una notificación.

El ejecutor no depende de SMTP ni de una base de datos. En pruebas se inyectan
implementaciones falsas en memoria. Si el correo falla, se registra el error,
`exito` queda en `False` y se continúa: las instrucciones posteriores son
independientes del envío fallido.

## API y transacciones

Al arrancar, la API inicializa las tablas y configura SMTP mediante
`DATABASE_URL`, `SMTP_HOST`, `SMTP_PORT` y `SMTP_FROM`. Cada petición recibe
una sesión de BD y el servicio de correo. `execute` valida el programa
completo, genera y optimiza el IR y ejecuta la VM con los repositorios de la
misma sesión. Los intentos se guardan en el historial.

Los errores de lenguaje impiden toda ejecución. Un fallo de correo no aborta:
el resultado indica `exito=False`, se ejecuta lo restante y se confirman las
escrituras de dispositivos y notificaciones. Ante un error fatal o una
excepción inesperada, el servicio revierte esas escrituras y guarda el
resultado en una transacción nueva. En un error fatal detectado por la VM,
los eventos anteriores describen acciones intentadas y un evento posterior
informa que se revirtieron. Ante una excepción inesperada, la respuesta
contiene un evento de error interno.

**Limitación:** un correo enviado antes de un aborto no se puede deshacer con
el rollback de la base de datos.
