# Ejecutor

`Ejecutor(repositorio, servicio_correo, registro_notificaciones).ejecutar(ir)`
recorre el IR con un puntero explícito. Usa la tabla de símbolos sobre el
repositorio inyectado para consultar y validar estados. `COMPARE` guarda un
booleano para `JUMP_IF_FALSE`; `HALT` termina. Cada llamada comienza con un
registro de comparación independiente.

El resultado contiene `exito`, errores y eventos ordenados. Los eventos de
`SET_STATE` incluyen dispositivo y estado; las consultas y los listados también
recogen los datos leídos. Los errores de IR o dispositivos abortan sin revertir
las acciones anteriores. Un máximo de 10 000 instrucciones evita bucles.

## Puertos

- `ServicioCorreo.enviar(destinatario, mensaje)` lanza `ErrorCorreo` si falla.
- `RegistroNotificaciones.registrar(mensaje)` registra una notificación.

El ejecutor no depende de SMTP ni de una base de datos. En pruebas se inyectan
implementaciones falsas en memoria. Si el correo falla, se registra el error,
`exito` queda en `False` y se continúa: las instrucciones posteriores son
independientes del envío fallido.

`SmtpServicioCorreo` implementa el puerto mediante `SMTP_HOST`, `SMTP_PORT` y
`SMTP_FROM`; utiliza Mailpit sin autenticación ni TLS y convierte los fallos de
envío en `ErrorCorreo`. La API todavía no está conectada a este adaptador.
