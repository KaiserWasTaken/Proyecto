# CommandFlow

Proyecto universitario de Lenguajes y Autómatas II: una aplicación web que
interpreta un lenguaje de comandos y opera dispositivos simulados, sin usar IA
ni lenguaje natural.

## Requisitos

- Git.
- Docker con Docker Compose.
- Python 3.12 y Node.js solo para pruebas o desarrollo fuera de Docker.

## Estructura

```text
CommandFlow/
├── backend/
│   ├── app/
│   │   ├── lexer/       # Análisis léxico
│   │   ├── parser/      # Análisis sintáctico
│   │   ├── ast/         # Nodos del árbol de sintaxis abstracta
│   │   ├── semantic/    # Tabla de símbolos y validación semántica
│   │   ├── ir/          # Representación intermedia
│   │   ├── optimizer/   # Optimizaciones del IR
│   │   ├── vm/          # Ejecución del IR
│   │   ├── api/         # Adaptador HTTP con FastAPI
│   │   ├── db/          # Persistencia con SQLAlchemy y PostgreSQL
│   │   └── services/    # Integraciones, incluido SMTP
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   └── src/             # Interfaz React y TypeScript
├── docs/                # Gramática y documentación del compilador
├── docker-compose.yml   # Los cuatro servicios
├── .gitignore
└── README.md
```

El procesamiento del lenguaje es independiente de FastAPI y de la base de
datos; la API y la persistencia actúan como adaptadores externos.

## Instalación con Docker Compose

Desde PowerShell:

```powershell
git clone https://github.com/KaiserWasTaken/Proyecto.git
cd Proyecto
Copy-Item .env.example .env
docker compose up --build
```

Si ajustas la contraseña de desarrollo, actualiza también las URL según se
explica abajo. Direcciones por defecto:

- Frontend: http://localhost:5173
- API: http://localhost:8001; documentación interactiva: http://localhost:8001/docs
- Mailpit: http://localhost:8025

Dentro de Compose, el backend usa `postgres:5432` y `mailpit:1025`.
`DATABASE_URL` y `SMTP_HOST` se usan al ejecutar el backend fuera de Docker.
Si cambias las credenciales de PostgreSQL, actualiza `DATABASE_URL` y
`DATABASE_URL_DOCKER` en `.env`; codifica para URL los caracteres especiales
en ambas, manteniendo la contraseña original en `POSTGRES_PASSWORD`.
Las credenciales de PostgreSQL se aplican al crear el volumen; si este ya
contiene datos, cambiar `.env` no modifica la contraseña almacenada.

### Si un puerto está ocupado

Cambia la variable correspondiente en `.env`:

| Servicio | Puerto del host | Variable |
| --- | --- | --- |
| Frontend | 5173 | `FRONTEND_PORT` |
| API | 8001 | `BACKEND_PORT` |
| PostgreSQL | 5433 | `POSTGRES_PORT` |
| Mailpit web | 8025 | `MAILPIT_WEB_PORT` |
| Mailpit SMTP | 1025 | `MAILPIT_SMTP_PORT` |

Si cambias el puerto de la API, ajusta `VITE_API_URL` y reconstruye el frontend
con `docker compose up --build`. Si cambias el puerto del frontend, ajusta
`CORS_ORIGINS` al nuevo origen. Si cambias el puerto de PostgreSQL, actualiza
el puerto de `DATABASE_URL` para el backend local; `DATABASE_URL_DOCKER` sigue
usando `postgres:5432`. Si cambias el puerto SMTP, ajusta `SMTP_PORT` para
el backend local. El enlace de Mailpit de la interfaz apunta a
`localhost:8025`; si cambias `MAILPIT_WEB_PORT`, abre el nuevo puerto manualmente.

### Reiniciar los datos

`docker compose down` conserva el volumen de PostgreSQL. Para borrar
**dispositivos, notificaciones e historial** y volver a los estados iniciales:

```powershell
docker compose down -v
docker compose up --build
```

## Pruebas y desarrollo local

Se requiere Python 3.12 o posterior (`requires-python = ">=3.12"`). Desde
PowerShell, en la raíz del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".\backend[dev]"
python -m pytest -c .\backend\pyproject.toml
```

FastAPI y Starlette tienen versiones fijadas en `backend/pyproject.toml`;
HTTPX también está fijado en las dependencias de desarrollo para las pruebas.
Los marcadores de integración y escenarios cubiertos están en
[pruebas](docs/pruebas.md).

Si el lanzador `py` no está disponible, utiliza la ruta al ejecutable de
Python 3.12 o posterior para crear el entorno virtual.

Para iniciar la API desde el directorio `backend`:

```powershell
# Desde la raíz, carga las variables del archivo local antes de iniciar la API.
Get-Content .\.env | Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
    $nombre, $valor = $_ -split '=', 2
    Set-Item -Path "Env:$nombre" -Value $valor
}
cd .\backend
uvicorn app.main:app --reload --port 8001
```

Los orígenes permitidos por CORS se configuran mediante `CORS_ORIGINS`,
separados por comas. Como alternativa se admite `FRONTEND_ORIGIN`
(por defecto `http://localhost:5173`); consulta
[backend/.env.example](backend/.env.example). La variable debe establecerse en el entorno antes de
arrancar el servidor.

## Preparación del frontend

Con el backend en marcha, abre otra terminal en la raíz y ejecuta:

```powershell
cd .\frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. La dirección de la API se configura con
`VITE_API_URL`; por defecto es `http://localhost:8001`. Puedes copiar
[frontend/.env.example](frontend/.env.example) a `frontend/.env` para
personalizarla y reiniciar Vite. El botón «Ejecutar» valida y ejecuta el
programa; el panel se actualiza con el estado almacenado.

Para comprobar la compilación: `npm run build` desde `frontend`.

La API utiliza un repositorio PostgreSQL; al arrancar carga cuatro dispositivos
solo si la tabla está vacía. También existe un repositorio en memoria para pruebas.

Los identificadores de dispositivos se comparan exactamente, sin normalización
y distinguiendo mayúsculas de minúsculas: `led1` y `LED1` son dispositivos
distintos. Esta regla se aplica al registro, la búsqueda y la actualización,
y debe mantenerse en cualquier implementación futura del repositorio.

## Regla de integración del análisis

El parser debe procesar los tokens disponibles incluso si el lexer informó
errores, para presentar ambos tipos de diagnóstico. El servicio de
aplicación no debe pasar al análisis semántico ni ejecutar instrucciones si
hay errores léxicos o sintácticos.

## Documentación

- [Arquitectura](docs/arquitectura.md)
- [Gramática y tokens](docs/gramatica.md)
- [AST](docs/ast.md)
- [Análisis semántico y tabla de símbolos](docs/semantica.md)
- [Representación intermedia](docs/ir.md)
- [Optimización](docs/optimizacion.md)
- [Ejecutor y transacciones](docs/ejecutor.md)
- [Modelo de base de datos](docs/base_de_datos.md)
- [Pruebas](docs/pruebas.md)
- [Guion de demostración](docs/demo.md)
