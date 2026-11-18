# CommandFlow

Proyecto universitario de Lenguajes y Autómatas II: una aplicación web que
interpreta un lenguaje de comandos y opera dispositivos simulados, sin usar IA
ni lenguaje natural.

## Estado

Está implementada la tabla de símbolos con un repositorio en memoria. El
lexer, parser, AST, analizador semántico, API, interfaz, base de datos y
Docker Compose aún no están implementados en este directorio.

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
├── docker-compose.yml   # Pendiente: frontend, backend, postgres y mailpit
├── .gitignore
└── README.md
```

El procesamiento del lenguaje se mantendrá independiente de FastAPI y de la
base de datos; la API y la persistencia serán adaptadores externos.

## Preparación del backend

Se requiere Python 3.12. Desde PowerShell, en la raíz del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".\backend[dev]"
python -m pytest -c .\backend\pyproject.toml
```

Si el lanzador `py` no está disponible, utiliza la ruta al ejecutable de
Python 3.12 para crear el entorno virtual.

La tabla de símbolos usa un repositorio en memoria inicializado con cuatro
dispositivos por defecto. Si se inyecta un repositorio, utiliza sus datos
existentes sin agregar dispositivos automáticamente.

El comando `docker compose up --build` se habilitará cuando se implementen
los servicios y sus archivos de configuración; todavía no está disponible.

## Flujo de Git sugerido

Inicializa Git si todavía no lo has hecho. Usa ramas por funcionalidad, por
ejemplo `feature/lexer`, `feature/parser` y `feature/semantic`. Mensajes de
commit sugeridos:

- `chore: initialize project skeleton`
- `docs: define command language grammar`
- `feat: implement command lexer`
- `feat: implement parser and AST`
- `feat: add language inspection CLI`
