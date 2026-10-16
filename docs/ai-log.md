
# Bitácora de IA (ai-log)

Registro de cómo usa el equipo los agentes de IA (Claude Code, OpenCode) para desarrollar
RestoAPI. Es un entregable de P3: deja trazabilidad de qué generó el agente, qué
aceptamos, qué corregimos y qué aprendimos para la siguiente HU.

## Cómo rellenarla

- **Quién:** la persona que lanzó la sesión con el agente. La entrada la escribe ella,
  no el agente (ver `AGENTS.md`, sección "Registro de IA").
- **Cuándo:** después de cada sesión relevante (genera código, tests o documentación, o
  sale una decisión). La entrada va en la **misma PR** que el trabajo.
- **Dónde:** en la sección de su HU, dentro de "Entradas". Si la sección no existe, se
  crea en orden numérico. Dentro de cada HU, la entrada más reciente va al final.
- **Cómo:**
  - Corta: debería llevar unos cinco minutos.
  - Causa raíz, no síntoma. "El agente se equivocó" no sirve; "el prompt no decía que
    el registro ignora el rol del payload (R-03)" sí.
  - Datos comprobables: commits, PR, tests o comandos, no de memoria.
  - Cita las reglas de `specs/ontology.md` por su id (R-xx).
  - Si un campo no aplica, escribe "nada"; no lo borres.
- **Lecciones:** si la misma lección sale en dos entradas, se propone como regla en
  `AGENTS.md` en una PR aparte.

## Plantilla

Copia este bloque en la sección de tu HU:

```markdown
#### AAAA-MM-DD · Título corto de la sesión · @usuario-github

- **Herramienta y modelo:** Claude Code · modelo / OpenCode · modelo gratuito
- **Issue y reglas:** #N · R-xx
- **Prompt clave:** el texto o un resumen
- **Resultado:** aceptado / aceptado con cambios / rechazado, y por qué
- **Errores o alucinaciones:** qué hizo mal o inventó, causa raíz y cómo se corrigió
- **Trabajo descartado:** qué se rehízo o no se usó, y por qué
- **Mi prompt o la spec:** qué faltaba o era ambiguo
- **Decisiones humanas:** reglas que faltaban y decidió una persona (quién)
- **Lección:** una línea para la próxima sesión
```

## Ejemplo (ficticio, solo para orientar)

```markdown
#### 2026-10-15 · Endpoint de registro · @usuario-ejemplo

- **Herramienta y modelo:** OpenCode · modelo gratuito X
- **Issue y reglas:** #00 · R-01, R-02, R-03
- **Prompt clave:** "Implementa POST /auth/register según la issue y specs/ontology.md"
- **Resultado:** aceptado con cambios. El endpoint y los tests eran correctos salvo el rol.
- **Errores o alucinaciones:** guardaba el `role` que llegaba en el payload, así que
  cualquiera podía registrarse como `admin`. Causa raíz: el agente no leyó la
  ontología. Corregido forzando `customer` y con un test que envía `role=admin`.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** el prompt no citaba R-03; lo daba por sabido.
- **Decisiones humanas:** nada
- **Lección:** citar en el prompt las reglas R-xx que afectan a la HU.
```

## Entradas

<!-- Una sección por HU: "### HU-XX · Título de la HU", con sus entradas debajo. -->

### HU-14 · Pantalla de facturas en el frontend

#### 2026-10-14 · Facturas y CSV para Excel (Frontend #38) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #32 · nada (UI sobre la API de la HU-14)
- **Prompt clave:** hacer la pantalla de facturas que faltaba en el frontend con los endpoints de Rita; después, "el CSV pierde datos cuando lo abro en Excel"
- **Resultado:** aceptado con cambios. Vista con pedidos por facturar, facturas emitidas con filtro de fechas y exportación CSV para el admin.
- **Errores o alucinaciones:** el CSV de la API (comas y punto decimal) salía en una sola columna en Excel en catalán. Causa raíz: el agente no tuvo en cuenta la configuración regional de Excel. Se comprobó abriéndolo con Excel y se convierte al descargar: `;`, coma decimal, fecha local y BOM. Al escribir el BOM desde la terminal se coló el carácter literal y el lint falló; se cambió por `\uFEFF`.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** no dije que el CSV era para abrirlo en Excel con configuración española.
- **Decisiones humanas:** no tocar el CSV de la API (es de Rita y sirve para contabilidad) y convertirlo solo en el frontend (Anna).
- **Lección:** probar las exportaciones con el programa con el que se van a abrir.

### HU-15 · Pantalla de estadísticas en el frontend

#### 2026-10-14 · Estadísticas de ventas (Frontend #39) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #33 · nada (UI sobre la API de la HU-15)
- **Prompt clave:** añadir las estadísticas en el frontend
- **Resultado:** aceptado. Total vendido, pedidos y ticket medio, ventas por día con su tabla, platos más vendidos y filtro de periodo.
- **Errores o alucinaciones:** el color principal no pasaba el validador de color para gráficos (poca saturación) y se eligió `#00879e` / `#2fa3b0`. En la primera captura, las barras de 10, 8 y 7 unidades medían lo mismo por un `max-width`; se corrigió al ver la captura, los tests no lo detectaban. Las ventas de ejemplo del modo simulado incluían los pimientos y rompían el test de borrar un plato; se limitaron los platos del historial.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** nada
- **Decisiones humanas:** nada
- **Lección:** mirar una captura del gráfico además de pasar los tests.

### HU-21 · Configuración de OpenCode con modelos gratuitos

#### 2026-10-14 · Configurar OpenCode y elegir modelos gratuitos · @costanna

- **Herramienta y modelo:** Claude Code para preparar la configuración y la documentación; OpenCode 1.18.34 para las pruebas · `opencode/big-pickle` (por defecto), `mimo-v2.6-flash-free`, `longcat-2.5-preview-free` y `nemotron-3-ultra-free` (comparación)
- **Issue y reglas:** #63 · nada (HU de configuración)
- **Prompt clave:** prueba de humo de la HU-20 ("¿Qué roles existen y qué no debes hacer?") con cinco modelos gratuitos, y revisión en modo `plan` de la migración 0006 de la PR #119 como prueba con una HU real
- **Resultado:** aceptado. Los cuatro modelos que respondieron dieron los 5 roles y las prohibiciones de `AGENTS.md`; big-pickle fue el más rápido (16 s) y se dejó por defecto en `opencode.json`. La revisión de la migración fue correcta (cadena 0004 → 0005 → 0006, conversión segura y pérdida de recuentos parciales al bajar).
- **Errores o alucinaciones:** `ling-3.1-flash-free` devolvió un error del servicio. En la revisión, big-pickle avisó de un caso con `quantity = 0` que no puede darse porque la BD exige `quantity > 0`: solo tenía la migración adjunta, no el modelo.
- **Trabajo descartado:** `ling-3.1-flash-free` como opción
- **Mi prompt o la spec:** en `opencode run`, la opción `-f` se tragó el texto de la pregunta como si fuera otro fichero; el mensaje tiene que ir antes de `-f`.
- **Decisiones humanas:** big-pickle por defecto para todo el equipo aunque yo uso mi propio proveedor (lo cambio con `/models`); documentar OpenCode en el README (Anna).
- **Lección:** para consultas que no deben tocar ficheros, usar `--agent plan`, y adjuntar con `-f` todo lo que la pregunta necesita (por ejemplo, el modelo además de la migración).

### HU-24 · Filtros admin de usuarios

#### 2026-10-15 · Spec, filtros, búsqueda y paginación de GET /users · @arita-pereira

- **Herramienta y modelo:** Claude (claude.ai, no Claude Code) · Opus 5.5
- **Issue y reglas:** #67 · R-11 (`include_deleted` de HU-32)
- **Prompt clave:** "empezamos el HU-24", con el estado del proyecto adjunto; la issue solo tenía la historia, sin criterios de aceptación
- **Resultado:** aceptado. Spec en `specs/HU-24-filtros-admin.md` y `GET /users/` con `Page[UserOut]`, `role`, `is_active` y `q`. 589 tests en verde con SQLite y Postgres 16.
- **Errores o alucinaciones:** en la cabecera de la spec puso "Aprueba: Levi (PO)", copiado de `specs/HU-TEMPLATE.md`. Causa raíz: la plantilla y la DoD de `AGENTS.md` aún dicen que aprueba Levi, pero el equipo ya no depende de él. Corregido a "Revisa y aprueba: Manon". Además, no preparó los comentarios de cada paso para el issue hasta que lo eché en falta.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** la issue no tenía criterios de aceptación; los fijó la spec con cuatro preguntas (formato, filtros, búsqueda y orden).
- **Decisiones humanas:** `Page[UserOut]` aunque sea breaking-api, filtros `role` + `is_active`, un solo `q` en nombre o email, orden fijo por `id` (Rita).
- **Lección:** leer `AGENTS.md` y `dev` antes de empezar funcionó otra vez: detectó que la PR #110 había vuelto a exigir spec por HU, y que HU-32 ya fijaba `include_deleted`.

#### 2026-10-15 · Revisión de Manon: acentos, longitud de q y skip/limit · @arita-pereira

- **Herramienta y modelo:** Claude (claude.ai, no Claude Code) · Opus 5.5
- **Issue y reglas:** #67 (PR #126 ya integrada) · nada
- **Prompt clave:** los tres comentarios de Manon en la PR #126
- **Resultado:** aceptado. Búsqueda sin acentos con `translate()` (`app/core/text_search.py`), `q` con máximo 100 caracteres y casillas de la spec marcadas.
- **Errores o alucinaciones:** en la PR #126 el agente afirmó que los tests pasaban "con SQLite y con Postgres 16", y era falso: `tests/conftest.py` usa siempre SQLite en memoria, aunque se le pase la URL de Postgres. Causa raíz: dio por bueno que cambiar `DATABASE_URL` cambiaba la base de datos de los tests, sin leer el `conftest.py`. Por eso no vio que el `lower()` no quita los acentos. Corregido probando la consulta directamente contra Postgres. Además, el primer intento (48 `replace()` anidados) desbordó la pila de SQLite.
- **Trabajo descartado:** los `replace()` anidados; la extensión `unaccent` (migración y no existe en SQLite).
- **Mi prompt o la spec:** la spec no decía nada de acentos, aunque el equipo trabaja con nombres en español y portugués.
- **Decisiones humanas:** `translate()` sin migración; `skip`/`limit` sin 422, solo la etiqueta `breaking-api` (Rita).
- **Lección:** antes de decir "probado en X", comprobar qué base de datos usan los tests de verdad.

### HU-25 · Cambio de contraseña y edición del propio perfil                                                                                                                     
                                                                                                                                                                                   
#### 2026-10-15 · Perfil propio y cambio de contraseña con un equipo de agentes · @levifvy                                                                                       
                                                                                                                                                                                   
- **Herramienta y modelo:** Claude Code · Opus 5.5. Usé un agente líder que coordinaba a cinco ayudantes, cada uno con una parte del trabajo: los datos de entrada, las reglas,  
los endpoints, los tests y la documentación.                                                                                                                                     
- **Issue y reglas:** #68 · R-01, R-02, R-03, R-04, R-11                                                                                                                         
- **Prompt clave:** le pedí que hiciera de líder del equipo para la HU-25 y que, antes de empezar, me confirmara qué campos del perfil se podían editar, cómo funcionaría el     
cambio de contraseña y dónde irían los endpoints. Cada ayudante debía tocar solo sus archivos y esperar a que terminara el anterior.                                             
- **Resultado:** aceptado. Ahora cualquier usuario puede editar su nombre, email y teléfono, y cambiar su contraseña indicando la actual. No hizo falta tocar la base de datos.  
Al final todo pasaba los tests (620) y el lint estaba limpio. Commits principales: 95fc335 (spec), 97222c7 (código), be56010 (tests), f601792 (docs) y f01523b (merge con `dev`).
- **Errores o alucinaciones:** el código salió bien a la primera. Lo que falló fue mi prompt, que no coincidía con el estado real del repo, y el agente me lo señaló al leerlo:  
daba por borrada una carpeta antigua que aún tenía restos, mencionaba una spec y una colección Bruno que todavía no estaban en `dev`, y no tenía en cuenta que la sección        
`/users` era solo para admins. Si se hubiera hecho tal cual, un cliente no habría podido editar su perfil; se resolvió con un router aparte. Además, el primer intento de commit 
falló por un error de sintaxis en el comando, sin llegar a guardar nada, y se repitió bien.                                                                                      
- **Trabajo descartado:** la colección Bruno, porque aún no se había subido al repositorio. Tampoco hizo falta migración.                                                        
- **Mi prompt o la spec:** di por hecho cómo estaba `dev` sin comprobarlo (aún no se habían aceptado algunas pull requests) y no pensé en dos casos: usuarios que entran solo con
Google o GitHub y no tienen contraseña, y alguien que "cambia" la contraseña por la misma. También olvidé que `AGENTS.md` pide escribir la spec antes del código; la redactó el  
agente, la revisé y la commiteé primero.                                                                                                                                         
- **Decisiones humanas:** las tomé yo y están en `specs/HU-25-cambio-password-perfil.md`:                                                                                        
  - si la contraseña actual es incorrecta se devuelve 403 y no 401, para que no parezca que la sesión ha caducado;                                                               
  - si alguien intenta cambiarse el rol o la activación desde su perfil, se rechaza con un error en vez de ignorarlo en silencio;
  - una cuenta sin contraseña no puede usar este cambio (lo cubrirá la HU de recuperación);
  - no se acepta como nueva la misma contraseña;
  - los endpoints van en `/users/me`;
  - equipo de cinco ayudantes, aunque el agente proponía tres;
  - revisores de la spec: Ana, Carla, Manon y Rita.
  - **Después del trabajo:** mientras trabajábamos se aceptó en `dev` la HU-24, que tocaba los mismos archivos. El agente unió los cambios de las dos historias sin perder nada y
  volvió a pasar todos los tests. También dejé documentado cómo trabajó cada ayudante en `docs/agents/HU-25/`.
  - **Lección:** comprobar el estado de `dev` antes de dar contexto al agente, y escribir la spec primero aunque la historia parezca pequeña.


### HU-26 · Swagger y auth

#### 2026-10-16 · Spec, Swagger de /auth y /users y test de contrato · @arita-pereira

- **Herramienta y modelo:** Claude (app de Claude, no Claude Code) · Sonnet 5.5 hasta el paso 2; Opus 5.5 desde el paso 3
- **Issue y reglas:** #69 · R-01, R-02, R-03, R-04, R-11 (citadas en las descripciones de Swagger)
- **Prompt clave:** "seguimos con el HU-26, primero hay que leer AGENTS.md y los specs"; después, "faltan los criterios de aceptación, se deberían escribir ahora"
- **Resultado:** aceptado. Criterios escritos a partir de una auditoría del `/openapi.json` real de `dev`. Spec en `specs/HU-26-swagger-auth.md`, helper `app/core/openapi.py` y 15 endpoints de `/auth` y `/users` documentados (tags, rol, errores con su `code`, ejemplos). `tests/test_openapi.py` falla si llega un endpoint nuevo sin documentar (probado en falso). Ruff limpio y 746 tests en verde con SQLite. Commits: 7ee820b (spec), 45e688e, ea89e79, 89867d9, 3db8f0f, 5dc6dd9, 799d538 y cdb40a4.
- **Errores o alucinaciones:**
  - Documentó todo 422 con `errors` obligatorio, pero los 422 de negocio (`redirect_uri_not_allowed`, `same_password`) solo traen `detail` y `code`. Causa raíz: dio por hecho que todo 422 venía de la validación de Pydantic, sin leer los `UnprocessableError` de los services. Lo vio el agente en el paso 5 y lo confirmó llamando a la API. Corregido con `errors` opcional y un test con el cuerpo real (5dc6dd9).
  - Le pedí los comandos para commitear los pasos 0 y 1 y los ejecutó él en mi ordenador. Causa raíz: tomó "puedes añadirlos a git add y git commit" como una orden de hacerlo. Como la carpeta conectada no deja borrar, git dejó un `HEAD.lock` (el agente lo apartó) y temporales en `.git/objects`. Desde entonces, el agente solo me pasa los comandos y los ejecuto yo.
- **Trabajo descartado:** la excepción de `/users/me*` en el criterio del 422, que se quitó cuando Levi dio el visto bueno.
- **Mi prompt o la spec:** la issue no tenía criterios de aceptación. La spec dio por fijos 13 endpoints, pero mientras trabajábamos HU-52 añadió 2 en `/auth` y `/users`. El agente lo detectó al revisar `dev` antes del paso 5.
- **Decisiones humanas:** módulo compartido `core/openapi.py` y tocar `main.py`; prioridad Must y que revise la primera persona que la vea (Rita). Alinear `/users/me*` con el helper (Levi dio el visto bueno el 16/10). Incluir los endpoints de HU-52 avisando a Anna, dejar fuera de esta HU la contraseña sin mínimo de `UserCreate` y `UserUpdate` (R-02), y una sola PR aunque pase de 400 líneas, revisada por commits (Rita).
- **Lección:** antes de documentar un error, provocarlo y validar el cuerpo real contra el modelo documentado.

### HU-27 · Colección Bruno para pruebas de la API

#### 2026-10-15 · Verificación end-to-end de la colección e integración de dev · @levifvy

- **Herramienta y modelo:** Claude Code · Opus 5.5 (`claude-opus-5-5`); Bruno CLI (`npx @usebruno/cli`) para ejecutar la colección
- **Issue y reglas:** #70 · R-02 (la colección comprueba que `password`/`password_hash` no salen), R-04 (baja lógica con `deactivate`)
- **Prompt clave:** "Verificar HU-27 end-to-end y arreglar lo que impida el 130/130", con diagnóstico paso a paso (el agente propone un comando, yo lo ejecuto y le pego la salida) y sin tocar `app/`, `tests/` ni `migrations/`
- **Resultado:** aceptado. La colección pasa 130/130 requests y 332/332 tests en local, antes y después de integrar `dev`. No hizo falta tocar código: el fallo era de entorno. Los commits están en la PR de HU-27 (colección, spec y diagramas); la rama se rebasó después sobre `dev`, así que no se citan hashes.
- **Errores o alucinaciones:** nada inventado por el agente en esta sesión. El 130/130 en rojo no era de la colección: el contenedor `api` salía con `Exited (1)` porque `alembic upgrade head` fallaba con `DuplicateTable: relation "categories" already exists`. Causa raíz: el volumen de Postgres tenía las tablas creadas por `Base.metadata.create_all` (lo llaman `app/main.py` y `create_admin`) sin `alembic_version`, y el `set -e` de `docker-entrypoint.sh` paraba el arranque. Se corrigió con `docker compose down -v`, levantando la API antes de crear el admin. Además, el README y `collection.bru` decían que la colección cubría "los 43 endpoints", cuando cubría 42 (`/auth/register` ya estaba fuera); con `dev` son 46 y se cubren 42.
- **Trabajo descartado:** `alembic stamp head` sobre las tablas existentes, porque el esquema de `create_all` podía no coincidir con el de las migraciones y la BD local habría quedado distinta de CI y producción.
- **Mi prompt o la spec:** la spec no decía en qué orden preparar el entorno local (API migrada antes que `create_admin`); se ha añadido en "Testing Decisions". Tampoco preveía qué hacer con endpoints que llegan de `dev` a mitad de la HU.
- **Decisiones humanas:** borrar el volumen local en vez de hacer `stamp` (Levi); dejar fuera de la colección `POST /auth/social/{provider}` (HU-38), `DELETE /users/{id}` y `POST /users/{id}/restore` (HU-32), que se añadirán en la PR de su HU, y solo actualizar los textos (Levi); no subir `docs/Briefing del Proyecto.md` (Levi).
- **Lección:** cuando el runner falla al 100 % en pocos milisegundos, revisar antes `docker compose ps -a` y los logs de `api` que la colección; y volver a ejecutar Bruno cada vez que se integra `dev`.

#### 2026-10-16 · Correcciones tras la revisión de Ana · @levifvy

- **Herramienta y modelo:** Claude Code · Opus 5.5 (`claude-opus-5-5`); Bruno CLI 4.2.1
- **Issue y reglas:** #70 · R-01, R-02, R-04, R-11, R-14
- **Prompt clave:** revisar la rama punto por punto contra la revisión de Ana (con archivo y línea, sin tocar nada) y luego aplicar las correcciones en commits atómicos, sin entrar en `app/`, `tests/`, `migrations/` ni CI.
- **Resultado:** aceptado. Ana acertaba: Production no tenía freno y la contraseña de prueba se deducía del email. Al rebasar salió lo que ella no vio: la colección daba 128/130 porque `09-list-users` esperaba un array y `GET /users/` ya es `Page[UserOut]` (HU-24), y `03-get-bartender` daba 404 porque el pedido solo tenía líneas de cocina (R-14, HU-40). Con eso resuelto y 9 requests nuevos para `/users/me`, cierra en 141/141 requests, 361/361 tests y 44 de 48 endpoints. Production queda de solo lectura, la contraseña es un uuid v4, la spec se llama ya `HU-27-coleccion-bruno.md` y `bruno/` sale de la imagen Docker.
- **Errores o alucinaciones:** el 130/130 del 15/10 se midió sobre un `dev` sin HU-24, HU-25 ni HU-40; y la documentación daba por inexistentes endpoints que ya estaban mergeados. Al generar los requests de error de `/users/me`, una sustitución de shell rompió un `{{tokenCustomer}}`; el agente lo vio al revisar el diff antes del commit. También quedó anotado que cambiar la contraseña no revoca los tokens ya emitidos: ninguna regla lo exige.
- **Trabajo descartado:** marcar el 404 del bartender como esperado (no probaba el caso feliz de R-14), `crypto.randomUUID()` porque no existe en el sandbox `safe`, y quitar el `create_all` de `app/` aquí porque se sale de HU-27.
- **Mi prompt o la spec:** la spec no obligaba a re-ejecutar la colección tras un rebase, y la excepción de alcance del diff no contemplaba `.dockerignore`. Lo añadimos con fecha.
- **Decisiones humanas (Levi):** Production de solo lectura; contraseña aleatoria; opción A para el bartender (una línea de barra de verdad, no un 404 esperado); sacar `bruno/` y `scripts/generate_agent_diagrams.py` de la imagen; citar la PR en vez de hashes, porque con squash quedarían huérfanos; incluir los dos requests de HU-25 aquí; y abrir issues aparte para el job de Bruno en CI y para el `create_all` de `app/main.py`. La PR se integra con squash.
- **Lección:** volver a ejecutar la colección después de cada rebase, no solo cuando mergea `dev`. Y sin un job de Bruno en CI, cualquier cambio de contrato la rompe sin que nadie se entere.

### HU-31 · Límite de intentos de login

#### 2026-10-16 · Spec, límite del login y del código 2FA · @arita-pereira

- **Herramienta y modelo:** Claude (app, sesión con el repo clonado en solo lectura) · Opus 5.5 para spec, código y revisión; Sonnet 5.5 para comentarios y mensajes
- **Issue y reglas:** #74 · R-10, R-12 (interacción con la 2FA de HU-37)
- **Prompt clave:** el texto de la issue y "mira AGENTS.md y specs primero"; después, una pregunta cada vez con opciones y una recomendada, hasta cerrar las 12 decisiones de la spec
- **Resultado:** aceptado con cambios. `POST /auth/login` responde `429` `too_many_attempts` con `Retry-After` tras 5 fallos por IP + email en 15 minutos, y `POST /auth/2fa/verify` igual tras 5 códigos malos por usuario. Contadores en memoria (`cachetools`), sin modelo ni migración. Commits `5089235` spec, `3f6a710` error 429 y service, `42fe652` notas de la spec, `7093393` fixture de `conftest.py`, `fd7fc78` límite en el login, `6af1247` variables y `api.md`, `54cfc5e` y `8a5ceee` límite del código 2FA, `60527b3` spec y `api.md` de 2FA, y el último con `deploy.md` y este ai-log. 902 tests en verde (35 nuevos), cobertura 100 %, ruff limpio. Los tests se probaron en falso con 18 errores metidos a propósito y los detectaron todos.
- **Errores o alucinaciones:** (1) Para la IP del cliente, Claude propuso `FORWARDED_ALLOW_IPS="*"` en Render sin mirar cómo lo trata uvicorn. Al leer el código de uvicorn 0.54 se vio que así toma la primera IP de `X-Forwarded-For`, que la escribe el cliente, y el proxy de Render no la limpia: un atacante cambiaría de IP en cada intento. Causa raíz: propuso una configuración de memoria, sin comprobarla en la versión que usamos. Se cambió por `CLIENT_IP_HEADER`, que nunca lee `X-Forwarded-For`. (2) La primera propuesta no tuvo en cuenta `estado-proyecto.md`; lo vi yo y pedí que lo leyera. (3) Claude puso como último paso de la HU una comprobación en producción que solo puede hacer Anna, porque solo ella despliega. Causa raíz: no había leído `docs/deploy.md`. Lo pregunté yo, y la comprobación pasó a `docs/deploy.md`.
- **Trabajo descartado:** `FORWARDED_ALLOW_IPS="*"` (falseable); una tabla `login_attempts` (migración `0009` y depender de Carla antes del 19/10).
- **Mi prompt o la spec:** el título de la tarjeta decía "logout" y la historia era de login (R-10). HU-37 dejó en su Out of Scope "límite de intentos en `/auth/2fa/verify` (lo cubre la HU de rate limiting, R-10)", pero nadie lo había dicho: salió al traer `dev` a mitad de la HU, y se amplió la spec. `dev` cambió cuatro veces durante la HU (HU-33, HU-45, HU-34 y HU-37), y HU-37 dio conflictos en `auth.py` y `.env.example`.
- **Decisiones humanas (Rita):** clave IP + email; contadores en memoria; 5 fallos en una ventana fija de 15 minutos; un login correcto borra el contador; durante el bloqueo, también la contraseña correcta da `429`; `429` desde el sexto intento con `Retry-After`; cuentan todos los `401` y no los `422`; login social fuera; aviso `Login blocked` con IP y email; IP desde `CLIENT_IP_HEADER`; el código 2FA entra en la HU, por usuario; la comprobación en producción va a `docs/deploy.md`. Además, en HU-45 la regla del progreso pasó de R-15 a R-16, porque HU-33 (Levi) ya usaba R-15.
- **Lección:** antes de proponer una configuración de seguridad, comprobarla en el código de la versión que usa el proyecto. Y volver a revisar `dev` antes de cada paso: es la sexta HU en la que sale esta lección, así que la propongo como regla en `AGENTS.md`.

### HU-33 · Verificación de email y recuperación de contraseña

#### 2026-10-16 · Implementación con un equipo de agentes · @levifvy

- **Herramienta y modelo:** Claude Code · Opus 5.5 (`claude-opus-5-5`): un líder y 7 especialistas (modelo, repositorio, emails, servicio, endpoints, tests y docs), lanzados uno tras otro según `docs/agents/HU-33/lead.md`.
- **Issue y reglas:** #76 · R-01, R-02, R-04, R-09, R-11, R-13 y R-15 (definida en la spec de HU-33)
- **Prompt clave:** "sigue con la implementación". El líder lanza a cada especialista con su directriz y sus archivos exclusivos, revisa su `git diff` antes de lanzar al siguiente y exige `ruff` limpio y `pytest` entero en verde sin modificar ningún test existente.
- **Resultado:** aceptado. Columna `users.email_verified` y tabla `email_verification_tokens` (migración `0009` con backfill a `true`); helper común `app/core/one_time_tokens.py`; `POST /auth/verify-email`, `POST /auth/resend-verification` y `POST /auth/forgot-password`. La recuperación reutiliza `PasswordResetToken` y `POST /auth/set-password` de HU-52. `register`, `PATCH /users/me`, `set-password`, `POST /users/`, el login social y `create_admin` aplican R-15 sin cambiar sus respuestas; `UserOut` gana `email_verified`. Sin breaking-api y sin dependencias nuevas. 804 tests en verde (746 al empezar, 3 del test de documentación de HU-26 y 55 nuevos en `tests/test_email_verification.py` y `tests/test_forgot_password.py`), 99 % de cobertura (100 % en los archivos de HU-33) y `ruff` limpio. La colección Bruno no compara `UserOut` campo a campo y no hubo que tocarla. Los commits van en la PR de HU-33.
- **Errores o alucinaciones:** `agent-model` registró el modelo nuevo en `app/models/__init__.py`, un patrón que no usa ningún otro modelo. Causa raíz: el reparto del líder no le daba `app/main.py` ni `migrations/env.py`, donde se registran los modelos. El líder se lo devolvió y le asignó esas dos líneas. `agent-endpoints` no llegó a enviar su informe; el líder verificó el paso por su cuenta. Los 3 tests de más que aparecieron en ese paso no eran nuevos: el test de HU-26 se ejecuta una vez por endpoint y ahora cubre también los tres nuevos.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** la spec no fijaba tres cosas que salieron al implementar: el orden de las comprobaciones de `verify-email`, si el cambio de email en `/users/me` debía guardarse en un solo commit, y qué pasa con el tiempo de espera de `forgot-password` justo después de una invitación. `docs/deploy.md` no mencionaba la migración `0008`; se añadió junto con la `0009`.
- **Decisiones humanas (Levi):**
  * **Flujos de tokens y validación:**
    * `verify-email` valida la caducidad/uso del token (410) antes de comprobar si el usuario está activo (400), alineándose con `set-password`.
    * Las invitaciones recientes activan el tiempo de espera de 60 segundos en `forgot-password`, ya que comparten el modelo `PasswordResetToken`.
  * **Persistencia y cambios de email:**
    * El cambio de email en `PATCH /users/me` se realiza en dos commits para proteger los tests de `update_profile`. Se asume el riesgo de que falle el segundo commit y el email quede verificado.
    * Se aprueban los textos de correo propuestos por `agent-email`.
  * **Notificaciones para Anna (Impacto en Backend):**
    * El helper de tokens se movió a `password_token_service.py`.
    * `forgot-password` se integra en `router_password.py` y su repositorio estrena `get_latest_for_user`.
    * `set-password` ahora marca el campo `email_verified`. El comportamiento previo de HU-52 no se altera y sus tests pasan sin cambios.
- **Lección:** entregar a cada agente **todos los archivos impactados** (incluyendo registros globales como `main.py`) y **ejecutar la suite completa de tests** tras cada iteración previene desviaciones y detecta rupturas de contrato inmediatamente.

### HU-34 · Cobertura de tests ≥ 80 %

#### 2026-10-16 · Cobertura al 100 % y umbral del 98 % en el CI · @levifvy

- **Herramienta y modelo:** Claude Code · Opus 5.5 (`claude-opus-5-5`), coordinando a los subagentes `agent-tests` y `agent-ci-docs`.
- **Issue y reglas:** #77 · R-02, R-13, R-14.
- **Prompt clave:** Le pedí cubrir las 10 sentencias que nos faltaban para el 100% (partíamos del 99%), sin tocar código de `app/` ni usar pragmas, y subir el mínimo en el CI al 95-98%.
- **Resultado:** Aceptado. Metimos 5 tests nuevos y un caso más en un parametrize. Pasamos de 746 a 756 tests y tocamos el 100% de cobertura. Además, dejamos el cerrojo en `ci.yml` con un umbral del 98%.
- **Errores o alucinaciones:**
  - El agente líder contó de memoria 12 ejecuciones de tests nuevas en vez de las 10 reales; lo pilló el subagente de tests al medir con pytest (746 → 756).
  - Aseguró que `docs/agents/` no existía en `dev` y se lió con las variables de producción. Causa raíz: no comprobó el repositorio ni miró bien `deploy.yml`.
  - Los comandos con saltos de línea largos se rompieron al copiarlos de la terminal y nos chafaron el orden de los commits. A partir de ahora, los comandos se ejecutan de uno en uno.
- **Trabajo descartado:** Los pragmas en `stats.py:75` y `social_providers.py:59-60` (ninguna línea era inalcanzable), un test aparte para la pareja `served` y la idea de poner el listón del CI al 100%, que nos habría obligado a meter pragmas con calzador.
- **Mi prompt o la spec:** La issue andaba desactualizada (pedía un 80% que ya pasábamos); lo que nos faltaba de verdad era proteger el CI para no ir hacia atrás. Además, en el prompt le pedí leer `pyproject.toml` y cosas de la HU-33 que aún no estaban en `dev`.
- **Decisiones humanas (Levi):** Dejar el 98% fijo en el YAML de CI, borrar la variable del repositorio para que no confunda, meter la info en `docs/agents/HU-34/` y negarme en rotundo a usar pragmas.
- **Lección:** Hay que medir antes de planificar (casi nos ponemos a picar código sin ver que ya estábamos en el 99%) y obligar al agente a comprobar el repositorio antes de dar datos por buenos.

### HU-35 · Comandos y subagentes de OpenCode

#### 2026-10-15 · Comandos /tests, /seguridad y /migracion · @costanna

- **Herramienta y modelo:** Claude Code para escribir los comandos, el subagente y la documentación; OpenCode 1.18.34 con `opencode/big-pickle` para probarlos
- **Issue y reglas:** #78 · R-02 (contraseñas), R-13 (vinculación social) en la revisión de seguridad
- **Prompt clave:** `/seguridad c8f0ca1^..c8f0ca1` sobre el login social de la #116; `/tests` sobre `PATCH /orders/{order_id}/items/{item_id}` con unidades; `/migracion` sin argumentos para ver el número libre
- **Resultado:** aceptado con cambios. `/seguridad` dio 3 hallazgos medios y 6 bajos sin tocar ficheros; comprobé cuatro (sin longitud máxima en `code` y `redirect_uri`, `get_by_id` sin comprobar en la línea 59, `downgrade` de la 0005 con `password_hash = ''` y `UserUpdate.password` sin mínimo) y son ciertos. `/tests` generó 24 tests que pasan con ruff limpio. `/migracion` respondió 0007, que es correcto.
- **Errores o alucinaciones:** la primera versión de `/migracion` se inventó la variable `ALCHEMY_DATABASE_URL` (es `DATABASE_URL`), escribió mal el nombre de la 0006 y no se paró en el paso 3 sin argumentos; el prompt no decía qué variable usar ni prohibía describir los pasos siguientes. Una ejecución de `/tests` terminó vacía y la siguiente funcionó. `opencode run` se quedaba esperando cuando la entrada estándar no se cerraba.
- **Trabajo descartado:** los 24 tests de `/tests`, que eran solo una prueba del comando; mis cambios no los necesitan.
- **Mi prompt o la spec:** en `/migracion` faltaba decir que sin argumentos no se ejecuta ningún comando y que los nombres se copian de la lista; se añadió.
- **Decisiones humanas:** el subagente de seguridad solo puede leer y usar `git diff`, `git log` y `git show`; los hallazgos de la #116 se pasan a Manon en lugar de arreglarlos, porque es su código (Anna).
- **Lección:** en un comando, decir cuándo parar y qué variables y ficheros existen; y en scripts, lanzar `opencode run` con `< /dev/null`.

### HU-36 · Revisión automática de PRs

#### 2026-10-16 · Revisión de cada PR con OpenCode en GitHub Actions (Backend #138) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5 para la spec, el workflow, el subagente `revisor` y el script del comentario; OpenCode 1.18.34 en GitHub Actions, primero con `opencode/big-pickle` y al final con `opencode/deepseek-v4.1-flash-free`
- **Issue y reglas:** #79 · nada
- **Prompt clave:** "haz la HU-36", con tres decisiones previas: el motor (OpenCode y un modelo gratuito), cuándo revisar (al abrir y en cada push) y si se podía nombrar OpenCode en el repo
- **Resultado:** aceptado con cambios. La revisión tarda unos 2-3 minutos y deja un único comentario que se actualiza en cada push; en la propia #138 se actualizó tres veces sin poner nunca la CI en rojo.
- **Errores o alucinaciones:**
  - La primera prueba en local agotó los 10 minutos: el agente recorría todo el repositorio. Causa raíz: sin límite de pasos y sin el diff adjunto. Se añadieron `steps: 12` y el diff como fichero.
  - En Actions, `big-pickle` se quedaba más de 10 minutos escribiendo la respuesta final. Con el mismo diff se probaron cuatro modelos gratuitos: `deepseek-v4.1-flash-free` (2 min 29 s), `space-bunny-free` (3 min 8 s, con frases en inglés) y `mimo-v2.6-flash-free` (no terminó en 7 min). Se eligió `deepseek`.
  - Al probar el script del comentario con un `gh` falso, en Windows se ejecutó el `gh.exe` real: solo hizo una lectura de una PR inexistente (404) y no escribió nada. Se repitió con `gh` definido como función.
  - El propio revisor encontró fallos reales en el workflow: tomaba la configuración del agente de la PR (podía ampliar sus permisos), no denegaba `task`, el paso del comentario podía poner la CI en rojo, había tuberías con `head` que `pipefail` podía cortar y variables en español (`AGENTS.md` pide inglés). Se corrigieron todos.
  - Al reescribir el YAML con un script se perdieron los `\` de continuación de línea y los `\n`; se arreglaron a mano y se validó con `bash -n`.
- **Trabajo descartado:** `big-pickle` como modelo; la acción oficial `anomalyco/opencode/github` (de terceros, con permisos de escritura); GitHub Models (no es OpenCode y puede necesitar que un admin de la organización lo active).
- **Mi prompt o la spec:** la spec no preveía cuánto tarda un modelo gratuito ni que, con `pull_request`, GitHub ejecuta el workflow de la propia PR; el segundo queda documentado como límite asumido.
- **Decisiones humanas:** OpenCode con un modelo gratuito; revisar al abrir y en cada push con un único comentario que solo informa; nombrar OpenCode y el modelo en el workflow, el README y la spec; cambiar a `deepseek` tras la prueba en GitHub (Anna).
- **Lección:** antes de elegir modelo para CI, medirlo con un diff real y un límite de tiempo, y limitar los pasos del agente.

### HU-37 · Verificación en dos pasos (TOTP)

#### 2026-10-16 · 2FA con TOTP en el backend y en la web (Backend #149, Frontend #56) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** #80 · R-02, R-12
- **Prompt clave:** "hazlo" (sobre la issue "Como usuario quiero autenticación en dos pasos (TOTP)"), después de elegir las opciones de la spec
- **Resultado:** aceptado con cambios. Spec primero; `POST /auth/2fa/verify` y `/users/me/2fa` (estado, `setup` con QR, `enable` con 8 códigos de recuperación y `disable`); el login y el login social devuelven `{mfa_required, mfa_token}` si el usuario tiene `totp_enabled`; secreto cifrado con Fernet y códigos guardados con SHA-256; migración 0010. En la web, el paso del código tras el login y la página Seguridad para todos los roles, también en el modo simulado (código `123456`). 26 tests de backend y 10 de frontend; la migración, probada en un Postgres temporal (sube, baja y vuelve a subir), y el flujo completo, en el navegador contra la API local con códigos TOTP reales.
- **Errores o alucinaciones:**
  - Cambiar el `response_model` del login a `TokenOut | TwoFactorChallengeOut` rompía `test_openapi.py` de la HU-26, que exige `TokenOut`. Se dejó `TokenOut` y el reto sale como `JSONResponse`: así no hubo que tocar ni esas líneas ni el test.
  - El QR no se veía en la web: `svg_inline()` de `segno` genera el SVG sin `xmlns`, y el navegador no lo muestra como imagen `data:`. El test solo miraba que empezara por `<svg`; se vio en la prueba con el navegador. Se genera el SVG completo y el test comprueba el `xmlns`.
  - En la página Seguridad, tras un código incorrecto el campo no se vaciaba y el siguiente código se pegaba detrás. Lo encontró el test del modo simulado.
  - Un test del login social con 2FA fallaba porque la sesión del fixture devolvía el usuario guardado en caché, sin la 2FA activada; se refresca antes de usarlo.
  - Mientras se preparaba la PR entró la HU-33 con su propia migración `0009`. La de esta HU pasó a ser la `0010`, y los conflictos en `auth.py`, `config.py` y `docs/api.md` se resolvieron solo añadiendo líneas (un import aparte en lugar de ampliar la línea de imports de otra persona).
  - La revisión automática de la PR señaló que los códigos de recuperación eran cortos (unos 48 bits, guardados con SHA-256 sin sal), que `totp_enabled` admitía `NULL` y que un test podía fallar por azar al usar `000000` como código incorrecto. Se corrigieron: códigos de 80 bits (`xxxxxxxxxx-xxxxxxxxxx`, con el límite del campo subido a 32 en la API y en la web), `nullable=False` con `false` por defecto y un código que seguro no es válido. Que el mismo código sirva varias veces en los 5 minutos del reto queda fuera, con el límite de intentos.
  - En la segunda pasada, el revisor vio que dos peticiones a la vez podían gastar el mismo código de recuperación. Se gasta con la fila del usuario bloqueada (`FOR UPDATE`, como en la HU-52) y se comprobó en Postgres: la segunda petición espera y después lo rechaza. También quitó los separadores `# ---` de los tests y pidió comprobar el 409 de `setup`.
- **Trabajo descartado:** la unión de tipos en el `response_model` y el import de `TwoFactorChallengeOut` en `auth.py`.
- **Mi prompt o la spec:** la spec decía que el secreto nunca sale en la API, pero `setup` tiene que devolverlo para teclearlo a mano; se corrigió. No tuvo en cuenta el test de Swagger de la HU-26.
- **Decisiones humanas:** login en dos pasos con un token temporal, 8 códigos de recuperación de un solo uso, que el login social también pida el código y hacer backend y frontend en la misma HU; los cambios en `auth.py`, `model_user.py` y la ontología, con el visto bueno del grupo (Anna).
- **Lección:** probar el flujo real en el navegador antes de la PR (los tests no vieron el QR roto) y comprobar el número de migración contra `dev` justo antes de subir.

### HU-38 · Inicio de sesión con Google y GitHub

#### 2026-10-14 · Spec e implementación del login social · @ManonChab

- **Herramienta y modelo:** Claude Code · Sonnet 5.5
- **Issue y reglas:** #81 (GitHub), #123 (Google) · R-13, R-01
- **Prompt clave:** "let's start HU-38" (14/10, 10:58). La spec y la implementación
  salieron de ahí, en dos PRs: #114 (spec) y #116 (código).
- **Resultado:** aceptado. Fusionado el 14/10. No se ha probado contra Google ni GitHub
  reales: hace falta una prueba de extremo a extremo cuando existan las apps (#115).
- **Errores o alucinaciones:** nada confirmado del agente. Un hueco que se cerró en la
  spec: un usuario creado por proveedor no tiene contraseña, y `/auth/login` habría dado
  500; ahora responde 401.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** el prompt era una sola línea y no citaba R-13 ni decía qué
  número de migración usar. La migración `0005` chocó con la de unidades de Anna y se
  renumeró a `0006` en #119. Causa raíz: la spec no reservaba número.
- **Decisiones humanas:** al investigar apareció configuración de despliegue (registrar
  las apps OAuth y cargar secretos en Render). Se pasó a Anna, responsable de DevOps
  (#115): ella registró la app de GitHub vinculada a la organización del equipo. Google
  necesita una cuenta de Gmail, que creará Manon. HU-38 es solo backend: la UI va en
  `Resto-API_Frontend#31`.
- **Lección:** antes de crear una migración de Alembic, mirar el número más alto en
  `origin/dev` y avisar al equipo; y citar en el prompt las reglas R-xx que afectan a
  la HU.

#### 2026-10-16 · Preparar el registro de la app de Google · @ManonChab

- **Herramienta y modelo:** Claude Code · Sonnet 5.5
- **Issue y reglas:** #123 (Google), #115 (apps OAuth y secretos) · nada (no hay código)
- **Prompt clave:** "let's start the next task HU-38, pull all current repo, read Kanban
  and necessary info", con la captura de la guía de Render y proveedores.
- **Resultado:** aceptado. No hay cambios de código: el agente comprobó que la HU-38 ya
  estaba fusionada (#114, #116, frontend #43) y que solo faltaba registrar el cliente de
  Google y cargar las variables en Render. Tradujo la guía al inglés. Sigue sin probarse
  contra Google real.
- **Errores o alucinaciones:** la guía de la captura usaba `restoapi.vercel.app`, que no
  es nuestra URL; el agente lo detectó comparando con `docs/deploy.md` y la issue #40 y
  propuso `apiresto-f5.vercel.app`. Además, el clon del backend estaba en una rama cuyo
  remoto se había borrado; se pasó a `dev` antes de leer nada.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** el prompt no decía que la HU ya estaba fusionada ni que la
  parte pendiente era externa al código; lo dedujo del Kanban.
- **Decisiones humanas:** los datos para registrar el cliente de Google se pasaron a Anna
  (DevOps y acceso a Render); sustituye lo anotado el 14/10 de que lo crearía Manon.
- **Lección:** comparar las URLs de una guía externa con `docs/deploy.md` antes de
  registrarlas como callback, y hacer `git branch -vv` para ver si la rama tiene remoto.

### HU-40 · Estación de barra en los pedidos

#### 2026-10-15 · HU-40_Estación de barra en los pedidos  · @ManonChab

- **Herramienta y modelo:** Claude Code with Sonnet 5.5
- **Issue y reglas:** #83
- **Prompt clave:**  "Read the necessary doc, the repo back and front, the kanban and let's start the new       H-40U,starting by spec definition"
- **Resultado:** aceptado 
- **Errores o alucinaciones:**
  - The one-line issue: I found the real gap by reading the code, and invented nothing.
  - The empty WebSocket assertion I wrote and then replaced.
  - The lazy="joined" draft I changed.
  - The two old tests that R-14 broke. I changed their data and didn't weaken them.
- **Trabajo descartado:** //
- **Mi prompt o la spec:**
    · ¿Qué entrega el backend en HU-40? Hoy el filtro por estación solo existe en el frontend (StationBoard); el  backend manda todo a cocina y a barra. → Filtrar en el backend (Recomendado)
    · El `status` del pedido es único (pending → in_kitchen → served) y hoy lo mueve cualquiera de cocina/barra. Con dos estaciones, ¿qué hacemos en esta HU? → Dejarlo como está (Recomendado)
    · En el pedido filtrado que ve `kitchen`/`bartender`, ¿qué se devuelve en `total`? → El del pedido completo (Recomendado)
    · Si el admin cambia la `station` de una categoría con pedidos abiertos, ¿qué pasa con las líneas ya creadas? → Se derivan en vivo (Recomendado)
    · Producción (Neon): las categorías existentes quedaron `kitchen` por defecto. ¿Cómo pasan Bebidas y Postres a `bar`? → Migración de datos
    · El enrutado por estación no está en la ontología (solo se cita como referencia externa). ¿Añadimos una regla R-14 a specs/ontology.md en el mismo PR? → Sí, R-14 (Recomendado)
- **Decisiones humanas:**

```text
   Tema     │                            Decisión                            │
├──────────────┼────────────────────────────────────────────────────────────────┤
│              │ El backend filtra según el rol: kitchen ve y marca solo líneas │
│ Alcance      │  kitchen, bartender solo bar, y admin/waiter ven todo. Esto    │
│              │ vale para GET /orders, GET /orders/{id}, PATCH .../items/{id}  │
│              │ y el WebSocket.                                                │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Contrato     │ Cada línea del pedido expone station. No hay parámetro         │
│              │ ?station=. total sigue siendo el del pedido completo.          │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Estado del   │ Sin cambios. El estado por producto o estación es HU-45 de     │
│ pedido       │ Rita, que toca el mismo router, así que hay que avisarla.      │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Estación de  │ Se deriva en vivo de la categoría actual del plato. No hay     │
│ una línea    │ columna nueva.                                                 │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Datos de     │ Migración 0007 que marca Bebidas y Postres como bar. Elegí     │
│ producción   │ esto frente a la opción recomendada, que era que el admin las  │
│              │ marcara.                                                       │
├──────────────┼────────────────────────────────────────────────────────────────┤
│ Ontología    │ Se añade la regla R-14 a specs/ontology.md en el mismo PR.     │
│              │ Necesita el visto bueno de Levi.
```

- **Lección:** //

### HU-41 · Pantalla de barra en tiempo real

#### 2026-10-14 · Pantalla de barra (Frontend #37) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** #85 · nada
- **Prompt clave:** empezar la HU-41: pantalla de barra en tiempo real como la de cocina
- **Resultado:** aceptado con cambios. Cocina y Barra comparten pantalla y cada plato va a una según el campo `station` de su categoría.
- **Errores o alucinaciones:** la primera versión daba por hecho que `station` llegaría con la HU-40; llegó antes con la #99 y encajó. Faltaba que el admin pudiera elegir la estación: en producción todas las categorías quedarían en cocina y Barra vacía. Se añadió el selector en Gestionar categorías.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** no pensé en cómo se rellenaría `station` en una BD que ya existe.
- **Decisiones humanas:** el estado del pedido lo lleva cocina salvo en los pedidos solo de barra (Anna).
- **Lección:** comprobar cómo queda una función nueva con los datos que ya hay en producción.

### HU-45 · Estado de plato

#### 2026-10-16 · Spec, progreso del pedido y documentación · @arita-pereira

- **Herramienta y modelo:** Claude (app, sesión con el repo clonado en solo lectura) · Sonnet 5.5 para comentarios y mensajes, Opus 5.5 para spec, código y revisión
- **Issue y reglas:** #89 · R-14, R-16 (nueva; era R-15, renumerada porque HU-33 ya usa R-15)
- **Prompt clave:** "Mira AGENTS.md y specs primero" y, con la historia de la issue, "falta escribir los criterios de aceptación. Escribe tú, juntamente con lo que se hará en cada paso"
- **Resultado:** aceptado con cambios. `ready_to_serve` por línea y `progress` por pedido (`stage` y `by_station`), calculados al responder, sin modelo ni migración. 18 tests nuevos, 764 en verde con SQLite, ruff limpio. Commits `51664c9` spec, `19a091e` pedido sin líneas, `96f8ec0` progreso, `03cbe7b` api.md.
- **Errores o alucinaciones:** (1) La tabla de `stage` de la spec daba `all_served` a un pedido sin líneas (0 de 0 servidas). Causa raíz: la regla se escribió sin pensar en el caso vacío. Se vio al implementar y se corrigió en `19a091e` (queda `waiting`). (2) Los comandos del paso 2 ponían `pytest` después de los commits y no tenían `ruff`. Causa raíz: el agente ordenó los comandos sin seguir "comprobar y después commitear". Lo vi yo y se corrigió. (3) Los tests pasaron a la primera; al meter errores a propósito, uno (restar los totales en lugar de sumar por líneas) no lo detectaba ningún test. Se añadió uno.
- **Trabajo descartado:** la regla "no se puede servir más de lo preparado" (cambiaba el código y los tests de Anna de la #117) y un `progress` solo con el total del pedido (sustituido por `by_station`).
- **Mi prompt o la spec:** la issue no tenía criterios y "estados más detallados" era ambiguo. No dije al principio que sala tenía que ver cocina y barra por separado; lo añadí al revisar la propuesta.
- **Decisiones humanas:** seguir permitiendo servir sin preparar (Anna, Discord, 16/10); `by_station` con las dos estaciones para `admin` y `waiter` (Rita); no cambiar el `status` del pedido automáticamente (Rita).
- **Lección:** probar los tests en falso: que pasen a la primera no demuestra que comprueben lo que importa.

### HU-46 · Estilo de la vista de pedidos del camarero

#### 2026-10-14 · Carta sin viñetas y aviso al repetir un plato (Frontend #34) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #26 · nada
- **Prompt clave:** quitar las viñetas al hacer un pedido y avisar al añadir otra vez el mismo producto
- **Resultado:** aceptado. Carta en rejilla y aviso dentro de la app al repetir un plato; los botones + y − no preguntan.
- **Errores o alucinaciones:** nada
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** la HU-47 (#27) pide quitar una de las dos formas de añadir platos; este cambio solo avisa.
- **Decisiones humanas:** aviso en lugar de quitar una forma de añadir (Anna).
- **Lección:** nada

### HU-48 · Paleta de restaurante con modo noche/día

#### 2026-10-14 · Colores, modo claro y oscuro, accesibilidad y botones táctiles (Frontend #36) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #28 · nada
- **Prompt clave:** colores de restaurante con modo oscuro, que pasen el filtro para personas con discapacidad visual y botones pensados para pantalla táctil
- **Resultado:** aceptado con cambios. Primero se hizo en crema y burdeos y el cliente pidió azules y verdes; se cambió.
- **Errores o alucinaciones:** simulando deuteranopia, los fondos de los estados verde y rojo casi no se distinguían; se añadió un símbolo a cada estado y bordes distintos en las mesas. Los textos se comprobaron con un script de contraste (AAA, 7:1) y de daltonismo.
- **Trabajo descartado:** la primera paleta en crema y burdeos.
- **Mi prompt o la spec:** no sabía los colores que quería el cliente hasta ver la primera versión.
- **Decisiones humanas:** azules y verdes en los dos modos (Anna, a petición del cliente).
- **Lección:** medir el contraste y simular el daltonismo con un script en vez de mirarlo a ojo.

### HU-49 · Pop-ups en lugar de menús desplegables para editar

#### 2026-10-14 · Formularios en ventana modal (Frontend #35) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #29 · nada
- **Prompt clave:** usar modales en el frontend
- **Resultado:** aceptado. Pedido, reservas, platos, categorías y mesas se editan en un modal con el foco dentro y Escape para cerrar.
- **Errores o alucinaciones:** un test pulsaba Nuevo plato antes de que se cargaran las categorías (el botón estaba desactivado). Al juntar ramas, colores y modales chocaban en `index.css` porque las dos añadían estilos al final; se movieron junto a sus reglas.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** "usa los modales" podía ser solo para los avisos; se aclaró que eran los formularios.
- **Decisiones humanas:** nada
- **Lección:** no añadir estilos al final de un CSS que tocan varias ramas a la vez.

### HU-51 · Reservas hechas por el cliente

#### 2026-10-15 · Asignación automática de mesa y límite de 8 personas (Backend #136) · @ManonChab

- **Herramienta y modelo:** Claude Code · Sonnet 5.5
- **Issue y reglas:** #106 · nada (la ontología no tiene reglas de reservas)
- **Prompt clave:** "let's start HU-51. review repos and contexto, we already have defined some specs in Spec de reservas hechas por el cliente- #124"
- **Resultado:** aceptado. Revisé el código a mano, sobre todo la comprobación de rol (`is_customer`) y la asignación de mesa. 22 tests nuevos (16 de integración y 6 unitarios), escritos primero y en rojo, y después el código. CI en verde en la PR #136 (Postgres). Commits: 6793260 (spec), 34acf7a (tests), 4ba9e46 (código) y 5320795 (docs).
- **Errores o alucinaciones:**
  - Ejecutó `ruff format tests` sobre toda la carpeta y reformateó unos 30 archivos ajenos. Causa raíz: formateó un directorio en vez de sus dos archivos. Se revirtió antes de commitear y la PR solo toca archivos de la HU.
  - Instaló `requirements.txt` en el Python global (3.14) en vez de usar el `.venv` del proyecto. Causa raíz: no comprobó si ya existía un entorno virtual (el proyecto usa Python 3.12).
  - El primer comando para aplicar los cambios falló por un error de comillas en el shell y no escribió nada; se repitió desde un archivo.
  - Los tests de HU-10 usan la fecha 10/10/2026, que ya es pasado, y con `reservation_in_past` habrían fallado. Lo vio al diseñar y usó fechas futuras (hoy + 30 días) en los tests nuevos.
- **Trabajo descartado:** el reformateo de los ~30 archivos de tests ajenos.
- **Mi prompt o la spec:**
  - La spec de #124 aún tenía tres `[NEEDS CLARIFICATION]` (si el cliente puede enviar `table_id`, si se rechaza el pasado y la prioridad). `AGENTS.md` pide cerrarlas antes de programar, así que se cerraron primero.
  - La spec no decía cómo sabe el servicio que el usuario es cliente (el agente añadió `is_customer`) ni cuántas mesas candidatas probar (límite de 100).
  - La spec no mencionaba que `reservation_in_past` rompe las fechas de los tests de HU-10.
  - `reserved_at` se guarda sin zona horaria y el agente lo comparó con la hora UTC actual, sin que la spec dijera nada de zonas horarias. Si el frontend enviaba hora local de España, una reserva cercana a "ahora" podía rechazarse por error (hasta 2 h). Anna confirmó el 16/10 que envía hora local sin zona y propuso comparar con la hora del restaurante; se corrigió con `RESTAURANT_TIMEZONE` (por defecto `Europe/Madrid`), `tzdata` en `requirements.txt` y 3 tests con el reloj congelado.
- **Decisiones humanas:** (Manon)
  - El `customer` puede seguir enviando `table_id`, para no romper el contrato ni los tests de HU-10.
  - Una reserva en el pasado se rechaza solo cuando la mesa se asigna automáticamente (422 `reservation_in_past`); con `table_id` no cambia.
  - Prioridad: Must.
  - Ya estaban acordadas por todo el equipo, Levi incluido, el 15/10: el cliente no elige mesa y el máximo es de 8 personas.
  - Comparar `reservation_in_past` con la hora del restaurante y no con UTC (Anna, 16/10).
- **Lección:** pedir al agente que formatee y edite solo los archivos de la HU, nunca carpetas enteras, y que use el `.venv` del proyecto.

#### 2026-10-16 · Reserva del cliente en la web (Frontend #51 y #52) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #51 (parte de frontend de #106) · nada
- **Prompt clave:** "he visto que el cliente no puede crear una nueva reserva" y después "comprueba si el apartado de reservas es igual al spec en back como en front"
- **Resultado:** aceptado con cambios. "+ Nueva reserva" para el cliente con día, hora, personas y notas, sin `table_id` y con hora local sin zona; aviso con más de 8 personas; el modo simulado aplica las mismas reglas que la API. 11 tests nuevos y probado contra la API de `dev` como cliente, camarero y en la demo.
- **Errores o alucinaciones:** la primera versión enseñaba al cliente "Mesa (id 3)", el id interno, porque el cliente no puede leer `/tables`. Salió al comparar con la historia 4 de la spec y se cambió por "Asignada por el restaurante", o "Mesa N" si la API devuelve `table_number`.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** la historia 4 ("ver la mesa que me han asignado") necesita el número de mesa, que la API no devuelve; se pidió `table_number` a Levi y Manon. Los criterios de aceptación de la spec eran solo de backend.
- **Decisiones humanas:** enviar la hora local sin zona, acordado con Manon el 16/10; mostrar "Asignada por el restaurante" hasta que la API envíe el número (Anna).
- **Lección:** comprobar cada historia de usuario de la spec, no solo los criterios de aceptación.

### HU-52 · Email para que el usuario cree su propia contraseña

#### 2026-10-15 · Invitación por email y página para crear la contraseña (Backend #137, Frontend #48) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5; el subagente `revisor` de OpenCode para revisar la PR del backend
- **Issue y reglas:** #107 · R-01, R-02, R-09
- **Prompt clave:** "haz mi issue pero no hagas PR, tráete antes todos los cambios que hay en dev"
- **Resultado:** aceptado con cambios. Spec primero; `POST /users/invite` y `POST /auth/set-password`; `PasswordResetToken` de un solo uso que caduca a las 48 h y del que solo se guarda el SHA-256; migración 0008; página `/crear-contrasena`. 19 tests de backend y 12 de frontend; la migración, probada en un Postgres temporal (sube, baja y vuelve a subir).
- **Errores o alucinaciones:**
  - El revisor encontró tres fallos de severidad baja: dos peticiones a la vez podían usar el mismo token, usuario y token se guardaban en dos transacciones y la creación y la caducidad salían de relojes distintos. Se corrigieron (bloqueo de la fila con `FOR UPDATE`, una sola transacción y el mismo reloj) y la carrera se comprobó en Postgres: la primera petición da 204 y la segunda 410.
  - Tras traer `dev`, un test del frontend fallaba porque su `vi.mock` de `config` no definía `GOOGLE_CLIENT_ID` (lo lee el login desde la HU-38); se añadió.
  - Probando en local, invitar daba 500: la copia de la base de datos tenía la 0005 marcada pero sin aplicar (`password_hash` no nulo). Era un fallo de la copia, no del código.
- **Trabajo descartado:** hacer opcional la contraseña de `POST /users/` (cambiaba el contrato y el código de la HU-32).
- **Mi prompt o la spec:** la spec no hablaba de concurrencia, transacciones ni de qué reloj usar para la caducidad.
- **Decisiones humanas:** endpoint nuevo `POST /users/invite` para cualquier rol, 48 h de validez, reutilizar `PasswordResetToken` y dejar fuera "he olvidado mi contraseña" y reenviar la invitación (Anna).
- **Lección:** pasar el revisor automático antes de pedir la revisión humana; aquí encontró tres fallos reales.

### HU-53 · Bitácora de IA

#### 2026-10-14 · Creación de la bitácora · @arita-pereira

- **Herramienta y modelo:** Claude (claude.ai, no Claude Code) · Opus 5.5
- **Issue y reglas:** #111 · nada (HU de documentación)
- **Prompt clave:** crear la bitácora usando como base la skill de retro de Manon
- **Resultado:** aceptado con cambios. El archivo final sigue la sección "Registro de IA" de `AGENTS.md` y añade ideas de la skill de Manon (causa raíz, trabajo descartado, autocrítica del prompt, lección).
- **Errores o alucinaciones:** la primera propuesta del agente llevaba un campo "Spec" (`specs/HU-XX.md`) y una skill para que el agente redactara la entrada. Causa raíz: la propuso antes de leer el repo; en `dev` ya estaba `AGENTS.md`, que dice que la entrada la escribe la persona, y el equipo decidió el 13/10 no hacer spec por HU. Se corrigió al revisar `dev`.
- **Trabajo descartado:** el campo "Spec" y el paso 3 (la skill).
- **Mi prompt o la spec:** no le dije que `AGENTS.md` ya definía el registro de IA ni que no hay spec por HU; lo descubrió al leer `dev`.
- **Decisiones humanas:** separar HU-21 en HU-21 (OpenCode, Anna) y HU-53 (bitácora, Rita), decidido por mí.
- **Lección:** antes de pedir una propuesta, pedir al agente que lea `AGENTS.md` y el estado de `dev`.

### Tarea #117 · Unidades preparadas y servidas

#### 2026-10-14 · Contar unidades (Backend #118 y #119, Frontend #42) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** #117 · relacionado con la HU-45 (#89)
- **Prompt clave:** "si hay 2 paellas se marcan como entregadas las 2 de golpe, ¿estaría bien para un restaurante?"
- **Resultado:** aceptado con cambios. `prepared_quantity` y `served_quantity` con migración que convierte los datos, compatible con `prepared` y `served`, y contador − 1/2 + en la web.
- **Errores o alucinaciones:** la migración de unidades entró con el número 0005 a la vez que la de login social (#116): dos cabezas y el CI de `dev` en rojo. Causa raíz: no se comprobó qué números usaban las PRs abiertas. Se renumeró a 0006 en la #119. Antes, la #108 de Manon movió `update_item` a otro fichero y hubo conflicto; se mantuvieron sus líneas y solo se cambió el bucle, con permiso de Anna.
- **Trabajo descartado:** la rama con la 0003 de `station`, que ya había entrado con la #109.
- **Mi prompt o la spec:** nada
- **Decisiones humanas:** contar unidades aunque solapa con la HU-45 de Rita; resolver el conflicto con el código de Manon sin tocar sus líneas (Anna).
- **Lección:** antes de mergear una migración, mirar los números de las PRs abiertas (de aquí sale el comando `/migracion`).

### Tarea #40 · Nombre APIResto y nueva URL

#### 2026-10-14 · Nombre visible y URL de producción (Frontend #41, Backend #120) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #40 · nada
- **Prompt clave:** cambiar en la app la parte visible de RestoAPI a APIResto y la URL de Vercel
- **Resultado:** aceptado. Título, cabecera y login con APIResto y enlaces a `apiresto-f5.vercel.app`.
- **Errores o alucinaciones:** al cambiar la URL, `ALLOWED_ORIGINS` quedó mal escrito en Render y el backend rechazaba todos los orígenes, también los antiguos; se detectó probando el CORS desde la terminal y se dejó con las dos URLs separadas por comas. La guía de la HU-38 usaba `restoapi.vercel.app`, que no es nuestra: registrarla como callback habría dejado los códigos de login en manos de quien la registrara.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** nada
- **Decisiones humanas:** mantener la URL antigua activa y aceptar las dos en `ALLOWED_ORIGINS` (Anna).
- **Lección:** después de tocar variables en Render, probar el login desde las dos URLs.

### Tarea Frontend #46 · La barra no lleva el estado de un pedido con platos de cocina

#### 2026-10-15 · Pedidos mixtos en la pantalla de barra (Frontend #49) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #46 · R-14
- **Prompt clave:** "soluciona en otra rama el error de la barra pero no lo subas a PR"
- **Resultado:** aceptado. La barra solo lleva el estado si sus líneas suman el `total` del pedido, que el backend sigue enviando completo. Probado en la app: en un pedido mixto sale "Cocina lleva el estado del pedido" y en uno solo de bebidas, "Empezar".
- **Errores o alucinaciones:** nada. Causa raíz del fallo: desde la HU-40 el backend solo envía a cada estación sus líneas, y la pantalla comparaba el número de líneas.
- **Trabajo descartado:** pedir `stations` en `OrderOut`, porque es código de Manon; queda como mejora.
- **Mi prompt o la spec:** nada
- **Decisiones humanas:** arreglarlo solo en el frontend sin tocar el backend de la HU-40 (Anna).
- **Lección:** cuando el backend cambia lo que envía a un rol, revisar la lógica del frontend que deduce cosas de esos datos.

### Tarea Frontend #47 · Probar la demo también en el despliegue

#### 2026-10-16 · Demo con los cambios guardados en el navegador (Frontend #50) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #47 · nada
- **Prompt clave:** "quiero que esté siempre la opción de demo, aunque esté en deploy" y "que la gente que entre en versión demo, una vez salga de la sesión, vuelva a estar como estaba"
- **Resultado:** aceptado con cambios. "Probar la demo" activa el modo simulado solo en ese navegador, sin llamar a la API; los cambios se guardan en el `localStorage` con versión, con "Empezar de cero" y "Salir de la demo". Probado con el build de producción.
- **Errores o alucinaciones:** un test fallaba porque guardaba un token antes de abrir el login y la app daba la sesión por iniciada; se guarda justo antes del clic.
- **Trabajo descartado:** usuarios demo reales en producción (la contraseña del admin sería pública) y recordar la demo por IP (en clase todos salen por la misma IP, en el móvil cambia y es un dato personal).
- **Mi prompt o la spec:** "según el IP" no encajaba con el objetivo; se planteó con tres opciones y se eligió por navegador.
- **Decisiones humanas:** demo por navegador y no por IP (Anna).
- **Lección:** cuando un requisito propone el cómo (la IP), preguntar por el qué antes de implementarlo.

### Tarea Frontend #54 · Botones de los pedidos y "Enviar a cocina" siempre a la vista

#### 2026-10-16 · Pedidos en tarjetas y barra de botones fija (Frontend #53) · @costanna

- **Herramienta y modelo:** Claude Code · Opus 5.5
- **Issue y reglas:** Frontend #54 · nada
- **Prompt clave:** "el camarero, al querer marcar el pedido, tiene que bajar hasta abajo del todo" y después "el botón enviar a cocina sigue bajando"
- **Resultado:** aceptado con cambios. Pedidos en tarjetas con la mesa, el estado y los botones arriba; barra de botones fija en las ventanas de formulario. Medido en 1366×600 y 390×700: el botón se ve arriba y a media carta.
- **Errores o alucinaciones:** el primer arreglo solo cubría la lista de pedidos y no la ventana de "Nuevo pedido"; lo detectó Anna al probarlo. Las capturas no lo mostraban porque la herramienta agranda la ventana a la página entera; se comprobó midiendo la posición del botón.
- **Trabajo descartado:** nada
- **Mi prompt o la spec:** nada
- **Decisiones humanas:** aplicar la barra fija a todas las ventanas de formulario, no solo a la de pedidos (Anna).
- **Lección:** probar la interfaz en pantallas bajas y medir, no solo mirar capturas.
