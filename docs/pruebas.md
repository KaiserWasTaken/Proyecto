# Pruebas

## Ejecución

Desde PowerShell en la raíz, con Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".\backend[dev]"
python -m pytest -c .\backend\pyproject.toml
```

HTTPX y pytest son dependencias de desarrollo. Las pruebas ordinarias usan
SQLite en memoria y correo simulado. Para excluir explícitamente todas las
integraciones externas:

```powershell
python -m pytest -c .\backend\pyproject.toml -m "not postgres and not mailpit"
```

### Integración opcional

- `postgres`: requiere un PostgreSQL accesible, tablas inicializadas y
  `DATABASE_URL` apuntando a PostgreSQL; de otro modo se omite si la URL no
  está configurada o no es PostgreSQL. Con Compose activo, puede usarse la
  URL local de `.env`. Las pruebas ejercitan transacciones con rollback.
- `mailpit`: requiere SMTP accesible en `SMTP_HOST:SMTP_PORT` y la API web de
  Mailpit en `http://localhost:8025`. Si SMTP no responde, se omite; si la API
  web no responde, la prueba falla. Los mensajes de prueba quedan en Mailpit.

Con los servicios de Compose activos, por ejemplo:

```powershell
$url = ((Get-Content .\.env | Where-Object { $_ -match '^DATABASE_URL=' }) -split '=', 2)[1]
$url = $url.Replace("@localhost:", "@127.0.0.1:")
if ($url -notmatch '[?&]connect_timeout=') {
    $separador = if ($url.Contains("?")) { "&" } else { "?" }
    $url += "${separador}connect_timeout=5"
}
$env:DATABASE_URL = $url
python -m pytest -c .\backend\pyproject.toml -m postgres -rs
$env:SMTP_HOST = "127.0.0.1"
$env:SMTP_PORT = "1025"
python -m pytest -c .\backend\pyproject.toml -m mailpit -rs
```

Si cambiaste `POSTGRES_PORT` o `MAILPIT_SMTP_PORT`, usa la URL local y el
puerto SMTP correspondientes. Las pruebas de Mailpit consultan el puerto
web 8025 fijo, por lo que este debe permanecer publicado para ejecutarlas.
El ejemplo usa `127.0.0.1` y un tiempo límite para evitar esperas largas al
resolver `localhost` o si PostgreSQL no responde.

## Escenarios funcionales

Todos los nombres de la tabla pertenecen a
[test_funcional.py](../backend/tests/test_funcional.py); cada prueba llama a
`POST /api/commands/execute` con SQLite en memoria y correo simulado.

| # | Escenario de la sección 16 | Prueba |
|---|---|---|
| 1 | `ENCENDER led1` | `test_encender_led1` |
| 2 | `APAGAR led1` | `test_apagar_led1` |
| 3 | `ACTIVAR alarma1` | `test_activar_alarma1` |
| 4 | `DESACTIVAR alarma1` | `test_desactivar_alarma1` |
| 5 | `CONSULTAR led1` | `test_consultar_led1` |
| 6 | `LISTAR DISPOSITIVOS` | `test_listar_dispositivos` |
| 7 | `ENCENDER dispositivo99` | `test_encender_dispositivo_inexistente` |
| 8 | `ENCENDER alarma1` | `test_encender_alarma_incompatible` |
| 9 | `ENCENDER` | `test_encender_sin_identificador` |
| 10 | `ENCENDER led1@` | `test_encender_con_caracter_invalido` |
| 11 | `NOTIFICAR "Prueba"` | `test_notificar_prueba` |
| 12 | `ENVIAR CORREO A "a@b.com" MENSAJE "Hola"` | `test_enviar_correo` |
| 13 | `SI led1 == ENCENDIDO ENTONCES APAGAR led1` | `test_si_led_encendido_apagar` (ambas ramas) |

El mismo archivo cubre el programa inválido sin ejecución, la equivalencia
del optimizador, la continuación tras fallo de correo y la validación sin
commit. `test_enviar_correo_real_desde_endpoint` comprueba el escenario de
correo con Mailpit real. Las pruebas de aborto y rollback están en
[test_api_ejecucion.py](../backend/tests/test_api_ejecucion.py), y la batería
de equivalencia en [test_optimizer.py](../backend/tests/test_optimizer.py).
