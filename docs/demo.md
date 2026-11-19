# Guion de demostración: 8–10 minutos

Antes de comenzar, inicia `docker compose up --build` y abre
`http://localhost:5173` y `http://localhost:8025`. Para partir de los estados
iniciales, opcionalmente ejecuta antes `docker compose down -v`: esto borra
todos los datos persistidos. Ejecuta cada bloque por separado en la consola.

1. **Listar (1 min).** Ejecuta `LISTAR DISPOSITIVOS`. Señala el evento y el
   panel: «Los cuatro dispositivos y sus estados provienen de PostgreSQL».
2. **LED (1 min).** Ejecuta `ENCENDER led1` y luego `APAGAR led1`. Señala el
   cambio visual: «El estado se actualiza al ejecutar cada instrucción».
3. **Alarma (1 min).** Ejecuta `DESACTIVAR alarma1` y luego `ACTIVAR alarma1`.
   Di: «Las operaciones válidas dependen del tipo de dispositivo».
4. **Consulta (30 s).** Ejecuta `CONSULTAR led1`. Di: «La consulta genera un
   evento con el estado actual sin cambiarlo».
5. **Errores (1–2 min).** Ejecuta por separado `ENCENDER led1@`, `ENCENDER`
   y `ENCENDER dispositivo99`. Señala fase, código, línea y columna:
   «Son errores léxico, sintáctico y semántico; no se ejecuta el programa».
6. **Condicional (1 min).** Ejecuta `ENCENDER led1`, después
   `SI led1 == ENCENDIDO ENTONCES APAGAR led1`. Di: «La VM comprueba la
   condición y ejecuta la acción solo si se cumple».
7. **Notificación (30 s).** Ejecuta `NOTIFICAR "Prueba"`. Di: «El evento se
   muestra y la notificación queda almacenada».
8. **Correo (1 min).** Ejecuta
   `ENVIAR CORREO A "a@b.com" MENSAJE "Hola"` y muestra el mensaje en
   Mailpit. Di: «El adaptador SMTP envía el mensaje al servidor de pruebas».
9. **Persistencia (1–2 min).** Ejecuta `ENCENDER led1` y comprueba el panel.
   En otra terminal, desde la raíz, ejecuta `docker compose restart backend`.
   Espera a que el backend esté disponible y recarga la página: `led1` sigue
   ENCENDIDO. Di: «Reiniciar el backend no elimina el volumen PostgreSQL».
