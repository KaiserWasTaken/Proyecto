# Arquitectura de CommandFlow

CommandFlow es una aplicación web que interpreta un lenguaje de comandos
definido por una gramática, no lenguaje natural ni IA. Controla dispositivos
simulados y permite consultar estados, registrar notificaciones y enviar
correos de prueba.

## Componentes y flujo

```text
Navegador
  React + TypeScript (frontend, nginx)
          |
          | HTTP: validar, ejecutar, consultar dispositivos
          v
  FastAPI (backend)
          |
          v
  Texto -> Lexer -> Parser -> AST -> Semántico -> IR -> Optimizador -> VM
                                  |                                  |  |
                                  |                                  |  +--> SMTP -> Mailpit
                                  +--> tabla de símbolos             |
                                             |                       |
                                             v                       v
                                       Repositorios PostgreSQL
                                       dispositivos / notificaciones / ejecuciones
```

El frontend envía el texto a `POST /api/commands/execute`, presenta los errores
o eventos ordenados y consulta `GET /api/devices` para actualizar el panel.
`POST /api/commands/validate` valida sin ejecutar ni escribir historial.

El lexer y el parser producen tokens, errores y AST; el parser procesa los
tokens disponibles incluso si hay errores léxicos. Si cualquiera de esas fases
falla, no se realiza el análisis semántico. El analizador semántico valida
todo el programa y produce instrucciones estructuradas; si hay errores, no
se ejecuta ninguna. El generador produce IR, el optimizador lo transforma y
la VM ejecuta las instrucciones restantes.

Las fases del lenguaje y la VM no dependen de FastAPI ni de PostgreSQL. La
semántica y la VM usan una interfaz de repositorio de dispositivos; la VM
también usa puertos de correo y notificaciones. El
[servicio de comandos](../backend/app/services/command_service.py) conecta
esas piezas con los adaptadores PostgreSQL y SMTP, y controla las
transacciones. Véanse [ejecutor](ejecutor.md) y
[base de datos](base_de_datos.md) para el manejo de fallos y persistencia.

## Agregar un comando

Según lo que necesite el comando:

1. Definir su sintaxis en [gramática](gramatica.md) y, si introduce palabras,
   añadir tokens y reconocimiento en [tokens.py](../backend/app/lexer/tokens.py)
   y [lexer.py](../backend/app/lexer/lexer.py).
2. Incorporar el nodo y su visitante en [nodes.py](../backend/app/ast/nodes.py)
   y la regla en [parser.py](../backend/app/parser/parser.py).
3. Añadir comprobaciones y la instrucción estructurada en
   [analyzer.py](../backend/app/semantic/analyzer.py) y
   [actions.py](../backend/app/semantic/actions.py); actualizar la tabla de
   símbolos si requiere nuevas operaciones o estados.
4. Traducirlo en [generator.py](../backend/app/ir/generator.py). Si necesita
   una operación nueva, definirla en [instructions.py](../backend/app/ir/instructions.py),
   ejecutarla en [executor.py](../backend/app/vm/executor.py) y revisar las
   barreras y saltos del [optimizador](../backend/app/optimizer/optimizer.py).
5. Si requiere efectos externos, definir o adaptar los puertos y sus
   implementaciones. Actualizar contratos HTTP o frontend solo si cambia la
   información expuesta, y añadir pruebas de cada fase y del comportamiento
   completo.
