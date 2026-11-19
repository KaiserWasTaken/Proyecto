# CommandFlow

Proyecto universitario de Lenguajes y Autómatas II: una aplicación web que
interpreta un lenguaje de comandos y opera dispositivos simulados, sin usar IA
ni lenguaje natural.

## Estado

Están implementados el lexer, el parser, el AST, el analizador semántico, la
tabla de símbolos en memoria, el IR, el optimizador y el ejecutor con puertos
inyectables. La API y la interfaz siguen siendo solo de validación; aún no
están conectadas al ejecutor. Compose incluye PostgreSQL y Mailpit como
servicios de apoyo; su integración, el CLI y el Compose completo están pendientes.

Consulta la [gramática y los tokens](docs/gramatica.md), los
[nodos del AST y Visitor](docs/ast.md), la [semántica](docs/semantica.md),
el [IR](docs/ir.md), la [optimización](docs/optimizacion.md) y el
[ejecutor](docs/ejecutor.md).

## Estructura prevista

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
├── docker-compose.yml   # PostgreSQL y Mailpit
├── .gitignore
└── README.md
```

El procesamiento del lenguaje se mantendrá independiente de FastAPI y de la
base de datos; la API y la persistencia serán adaptadores externos.

## Servicios de apoyo

Copia `.env.example` a `.env` y ajusta la contraseña de desarrollo. Después
ejecuta `docker compose up -d`. PostgreSQL escucha en el puerto indicado por
`POSTGRES_PORT` (5432 por defecto) y Mailpit en `localhost:1025`, con interfaz
en `http://localhost:8025`. Si cambias el puerto o las credenciales de
PostgreSQL, actualiza también `DATABASE_URL` en `.env`.
Las credenciales de PostgreSQL se aplican al crear el volumen; si este ya
contiene datos, cambiar `.env` no modifica la contraseña almacenada.

## Preparación del backend

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

Si el lanzador `py` no está disponible, utiliza la ruta al ejecutable de
Python 3.12 o posterior para crear el entorno virtual.

Para iniciar la API desde el directorio `backend`:

```powershell
cd .\backend
uvicorn app.main:app --reload
```

El origen permitido por CORS se configura mediante la variable de entorno
`FRONTEND_ORIGIN` (por defecto `http://localhost:5173`); consulta
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
`VITE_API_URL`; por defecto es `http://localhost:8000`. Puedes copiar
[frontend/.env.example](frontend/.env.example) a `frontend/.env` para
personalizarla y reiniciar Vite. El botón «Ejecutar» solo valida: los
dispositivos no cambian de estado.

Para comprobar la compilación: `npm run build` desde `frontend`.

La tabla de símbolos usa un repositorio en memoria inicializado con cuatro
dispositivos por defecto. Si se inyecta un repositorio, utiliza sus datos
existentes sin agregar dispositivos automáticamente.

Los identificadores de dispositivos se comparan exactamente, sin normalización
y distinguiendo mayúsculas de minúsculas: `led1` y `LED1` son dispositivos
distintos. Esta regla se aplica al registro, la búsqueda y la actualización,
y debe mantenerse en cualquier implementación futura del repositorio.

El despliegue completo con backend y frontend se incorporará más adelante;
por ahora Compose levanta únicamente PostgreSQL y Mailpit.

## Regla de integración del análisis

El parser debe procesar los tokens disponibles incluso si el lexer informó
errores, para presentar ambos tipos de diagnóstico. El futuro servicio de
aplicación no debe pasar al análisis semántico ni ejecutar instrucciones si
hay errores léxicos o sintácticos.

## Flujo de Git sugerido

Inicializa Git si todavía no lo has hecho. Usa ramas por funcionalidad, por
ejemplo `feature/lexer`, `feature/parser` y `feature/semantic`. Mensajes de
commit sugeridos:

- `chore: initialize project skeleton`
- `docs: define command language grammar`
- `feat: implement command lexer`
- `feat: implement parser and AST`
- `feat: add language inspection CLI`
