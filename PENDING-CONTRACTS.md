# Contratos pendientes · HU-09 (CRUD de mesas)

Rama: `feature/HU-09-crud-mesas` · Responsable: Levi · Creado: 05/10/2026

La HU-09 se ha empezado **antes** de que existan en `dev` el esqueleto de Carla (C-01) y los
contratos de Rita (R-04). Todo el código se ha escrito contra **firmas asumidas**, marcadas en el
código con `# ASSUMPTION:` y listadas aquí.

**Cómo cerrar un punto:** cuando el contrato real llegue a `dev`, haz merge en esta rama, compara la
firma real con la asumida y ajusta el código si hace falta. Después cambia el estado a ✅ y borra el
comentario `ASSUMPTION` correspondiente. Este fichero se borra antes de abrir el PR de la HU-09 a `dev`.

Estados: ⏳ pendiente · ✅ confirmado · ⚠️ difiere (hay que adaptar el código)

## 1. `app/core/database.py` (Carla, C-01)

| # | Firma asumida | Se usa en | Estado |
|---|---|---|---|
| D1 | `Base`: clase `DeclarativeBase` de SQLAlchemy 2.0 | `app/models/dining_table.py:12` (import), `tests/conftest.py:93` (`Base.metadata.create_all`) | ⏳ |
| D2 | `Base` **no** define `naming_convention` para `ck`. Si la define con `%(constraint_name)s`, renombrar los CHECK a `capacity_positive`, `location`, `status` | `app/models/dining_table.py:29-39` | ⏳ |
| D3 | `get_db()`: dependencia generadora **síncrona** que hace `yield Session` y la cierra en su `finally`. **No hace commit**: ni al terminar la petición ni en ningún otro momento. El router tampoco cierra la sesión | `tests/conftest.py:136` (`app.dependency_overrides[get_db]`), `app/routers/tables.py:14-16` (`DbSession`) | ⏳ |
| D4 | Como `get_db` no hace commit (D3), **el router confirma la transacción**. En POST, PUT y PATCH `/status`: `try` → servicio → `commit` → `refresh`; si falla, `except Exception` → `rollback` → `raise`. En DELETE: servicio (`db.delete`) → `commit`, sin `refresh`. Los GET no tocan la transacción. El servicio nunca hace commit, solo `add`/`flush`/`delete`. Si Carla hace que `get_db` haga commit, hay que quitar los `commit` del router | `app/routers/tables.py:89-162`, `app/services/dining_table_service.py:26-28` | ⏳ |

## 2. `app/main.py` (Carla, C-01)

| # | Firma asumida | Se usa en | Estado |
|---|---|---|---|
| M1 | `app.main` expone `app: FastAPI` | `tests/conftest.py:134` (fixture `client`) | ✅ |
| M2 | El lifespan de la app no necesita la BD de desarrollo para arrancar (en los tests solo se sobreescribe `get_db`) | `tests/conftest.py`, fixture `client` (`with TestClient(app)`) | ⏳ |

## 3. Modelos `roles` y `users` (Carla, C-01)

| # | Firma asumida | Se usa en | Estado |
|---|---|---|---|
| U1 | `app/models/role.py` → `Role(id, name, description)` y `app/models/user.py` → `User(id, name, email, password_hash, phone, role_id, is_active, created_at)`, según §3.1 | `tests/conftest.py:96`, `:157` (fixture `create_user`) | ⚠️ No hay tabla `roles`: el rol es la columna `users.role` (texto) con el enum `Role` en `app/models/model_user.py`. El conftest ya está adaptado (`make_user`) |
| U2 | Nombres de rol: `admin`, `waiter`, `kitchen`, `customer` | `tests/conftest.py:37-38` (`ROLE_NAMES`) | ✅ |
| U3 | Los roles pueden venir sembrados por migración (C-03). El conftest hace get-or-create y funciona en los dos casos | `tests/conftest.py`, fixture `create_user` | ✅ No aplica (no hay tabla `roles`) |
| U4 | `password_hash` usa bcrypt (`hashpw` / `checkpw`) | `tests/conftest.py:173` | ✅ |

## 4. Auth: `app/core/security.py` y `/auth/login` (Carla, C-03 / HU-04)

| # | Firma asumida | Se usa en | Estado |
|---|---|---|---|
| A1 | `POST /auth/login` con JSON `{"email", "password"}` → `200 {"access_token": str, "token_type": "bearer"}`. Si usa `OAuth2PasswordRequestForm` (form `username`/`password`), cambiar `_login_token` | `tests/conftest.py:205` | ⚠️ `/auth/login` usa `OAuth2PasswordRequestForm` (form `username`/`password`). Los tests generan el token con `create_access_token` y no pasan por el login |
| A2 | JWT HS256 firmado con `JWT_SECRET_KEY` | `tests/conftest.py:44-45` (`JWT_ALGORITHM`) | ✅ |
| A3 | Claims del JWT: `sub` = id del usuario (str), `role`, `exp`. Si `sub` es el email, ajustar `_stub_token` | `tests/conftest.py:193` | ⚠️ Claims: `sub` (id del usuario, str) y `exp`. No hay claim `role`: el rol se lee del usuario en la BD |
| A4 | **Stub de tokens activo** (`USE_STUB_TOKENS = True`). Poner a `False` cuando exista `/auth/login` y borrar `_stub_token` | `tests/conftest.py:41-43`, `:192` | ✅ Stub eliminado: el conftest usa `app.core.security.create_access_token` |
| A5 | `get_current_user()` y `require_role(*roles)` con la firma de §5.2. **Ojo:** mientras siga el stub que «devuelve un admin fijo», los tests de 403 para `waiter`/`customer` fallarán. Es lo esperado hasta el 06/10.<br>**Firma exacta asumida:**<br>• `get_current_user`: dependencia sin parámetros de ruta (`Depends(get_current_user)`). Lee el Bearer token, devuelve el `User` del ORM y lanza 401 si el token falta o no es válido.<br>• `require_role(*roles: str)`: **fábrica** variádica que devuelve una dependencia. Esa dependencia depende de `get_current_user` (sin token → 401), devuelve el `User` y lanza 403 si su rol no está en `roles`.<br>El router solo importa `require_role` y la usa en `dependencies=[Depends(require_role(...))]`: GET y PATCH `/status` → `"admin", "waiter"`; POST, PUT y DELETE → `"admin"`.<br>Los 401 (6 tests) y 403 (4 tests) llevan el marcador `xfail_auth_stub` (`pytest.mark.xfail(..., strict=False)`) mientras el stub de `security.py` siga devolviendo un admin fijo o no rechace peticiones sin token. Al sustituirlo por la implementación real, quitar el marcador. Los 401 solo comprueban `status_code`, no el formato `{"detail","code"}` — ver E1 | `app/routers/tables.py:18-22`, `:37-38` (`ADMIN_ONLY`, `ADMIN_OR_WAITER`), `tests/integration/test_tables.py` (`xfail_auth_stub`) | ✅ Implementación real en `app/core/permissions.py`: `require_role(*roles: Role)` y `get_current_user` devuelve el `User` del ORM. Marcador `xfail_auth_stub` eliminado |

## 5. Errores y paginación (Rita, R-04 / HU-11)

| # | Firma final | Se usa en | Estado |
|---|---|---|---|
| E1 | `app.core.exceptions`: `NotFoundError` (404), `ConflictError` (409), `ForbiddenError` (403) y `UnprocessableError` (422). Heredan de `HTTPException`; constructor `(detail: str, *, code: str \| None = None)`. Cada clase fija su `status_code` y un `code` por defecto, así que el servicio solo pasa el mensaje.<br>**Codes** (constantes en el mismo módulo): `NOT_FOUND_CODE="not_found"`, `CONFLICT_CODE="conflict"`, `FORBIDDEN_CODE="forbidden"`, `UNPROCESSABLE_CODE="unprocessable"`. Una subclase puede fijar el suyo (`ReservationConflict` → `"reservation_conflict"`).<br>**Handlers globales** (`register_exception_handlers(app)` en `main.py`): todas las respuestas de error son `{"detail": str, "code": str}`.<br>- `HTTPException` normal (por ejemplo los 401 de `security.py`): `code` según el status (`unauthorized`, `forbidden`, `not_found`, `method_not_allowed`...).<br>- **422 de validación:** `{"detail": "Invalid request data", "code": "validation_error", "errors": [...]}`. `errors` lleva `loc`, `msg` y `type` de cada campo, sin el valor enviado. Los tests pueden comprobar el formato.<br>- **500:** `{"detail": "Internal server error", "code": "internal_error"}`; el traceback va al log. | `app/services/dining_table_service.py`, `app/services/reservations.py`, `app/crud/crud_category.py`, `app/crud/crud_dish.py` | ✅ |
| P1 | `app.core.pagination`: `Page[Schema]` (`items`, `total`, `page`, `size`), `PageParams`, dependencia `page_params` y atajo `PageParamsDep`, y `paginate(db, stmt, params, Schema)`.<br>Query params: `page` ≥ 1 (por defecto 1) y `size` de 1 a 100 (por defecto 20). Una página más allá de la última devuelve `items` vacío.<br>`stmt` tiene que llevar `order_by` para que las páginas no repitan ni salten elementos.<br>**Pendiente:** migrar `GET /tables` a `Page[DiningTableRead]` + `paginate` y borrar `DiningTablePage` (Levi). | `app/routers/reservations.py`, `app/routers/router_dish.py`; pendiente `app/routers/tables.py` | ✅ (falta migrar mesas) |
| L1 | `app.core.logging.setup_logging()` (se llama en `main.py`): texto en local y JSON en producción (`ENVIRONMENT=production`), nivel con `LOG_LEVEL`. Un filtro oculta contraseñas, tokens, `Authorization`, claves y la contraseña de la URL de la BD.<br>Uso: `logger = logging.getLogger(__name__)` y `logger.info("Dish created", extra={"dish_id": dish.id})`. | Todo el proyecto | ✅ |

## 6. Herramientas y configuración

| # | Punto | Dónde | Estado |
|---|---|---|---|
| T1 | `# noqa: I001` temporal: mientras `app/core/` no exista, ruff clasifica `app.core` como paquete de terceros y pide otro orden de imports. Quitarlo cuando llegue el esqueleto | `app/models/dining_table.py:6-7`, `tests/unit/test_dining_table_service.py:6-7`. Dentro de `app/` no hace falta desde que existe `app/__init__.py` (el servicio y el router pasan sin `noqa`); fuera de `app/`, sí | ⏳ |
| T2 | No hay `pyproject.toml` ni `ruff.toml`: se ha usado la configuración por defecto de ruff (line-length 88) | Todos los ficheros nuevos | ⏳ (Carla y Anna) |
| T3 | Sin `app/core/`:<br>• `tests/unit/` → error de recolección (código 2) por el import top-level de `app.core.exceptions`.<br>• `tests/integration/` → skip por las fixtures de `conftest.py`.<br>En CI, `pytest` saldrá con código 2 (no 5) hasta que Carla mergee `app/core/` | `deploy.yml` (paso de pytest) | ⏳ |
| T4 | **Migración de `dining_tables` no creada** (§10 R8: Carla coordina las migraciones). Se crea cuando exista `alembic/` en `dev` | `alembic/versions/` | ⏳ |

## 7. Por aclarar con Rita

| # | Punto | Estado |
|---|---|---|
| R1 | El fichero se llama `RestoAPI-Plan-de-Proyecto-v3.pdf`, pero la portada y los pies de página dicen «Versión 2 · 02/10/2026». Trabajamos con el contenido v3 (`dining_tables`, `/tables`, código en inglés). Hay que confirmar con Rita y regenerar la portada | ⏳ |

## 8. Decisiones de diseño de la HU-09 (para validar como PO)

No son contratos con otras personas, pero conviene revisarlas en el PR:

- `PUT /tables/{id}` es un **reemplazo completo**: `DiningTableUpdate` exige `number`, `capacity`, `location` y `status`.
- `number` y `capacity` se validan con `> 0` en Pydantic (devuelve 422). En la BD solo `capacity` lleva CHECK, como dice §3.1.
- `location`, `capacity` y `status` son `NOT NULL` en la BD. §3.1 no lo indica, pero un valor nulo no tendría sentido. `status` tiene `DEFAULT 'available'`.
- Los esquemas de entrada usan `extra="forbid"`: un campo desconocido devuelve 422.
- Los valores permitidos de `location` y `status` se definen en un solo sitio (`app/schemas/dining_table.py`) y el modelo los importa de ahí.