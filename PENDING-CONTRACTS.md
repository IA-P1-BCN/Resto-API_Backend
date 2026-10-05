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
| D3 | `get_db()`: dependencia generadora que hace `yield Session` | `tests/conftest.py:136` (`app.dependency_overrides[get_db]`) | ⏳ |

## 2. `app/main.py` (Carla, C-01)

| # | Firma asumida | Se usa en | Estado |
|---|---|---|---|
| M1 | `app.main` expone `app: FastAPI` | `tests/conftest.py:134` (fixture `client`) | ⏳ |
| M2 | El lifespan de la app no necesita la BD de desarrollo para arrancar (en los tests solo se sobreescribe `get_db`) | `tests/conftest.py`, fixture `client` (`with TestClient(app)`) | ⏳ |

## 3. Modelos `roles` y `users` (Carla, C-01)

| # | Firma asumida | Se usa en | Estado |
|---|---|---|---|
| U1 | `app/models/role.py` → `Role(id, name, description)` y `app/models/user.py` → `User(id, name, email, password_hash, phone, role_id, is_active, created_at)`, según §3.1 | `tests/conftest.py:96`, `:157` (fixture `create_user`) | ⏳ |
| U2 | Nombres de rol: `admin`, `waiter`, `kitchen`, `customer` | `tests/conftest.py:37-38` (`ROLE_NAMES`) | ⏳ |
| U3 | Los roles pueden venir sembrados por migración (C-03). El conftest hace get-or-create y funciona en los dos casos | `tests/conftest.py`, fixture `create_user` | ⏳ |
| U4 | `password_hash` usa bcrypt (`hashpw` / `checkpw`) | `tests/conftest.py:173` | ⏳ |

## 4. Auth: `app/core/security.py` y `/auth/login` (Carla, C-03 / HU-04)

| # | Firma asumida | Se usa en | Estado |
|---|---|---|---|
| A1 | `POST /auth/login` con JSON `{"email", "password"}` → `200 {"access_token": str, "token_type": "bearer"}`. Si usa `OAuth2PasswordRequestForm` (form `username`/`password`), cambiar `_login_token` | `tests/conftest.py:205` | ⏳ |
| A2 | JWT HS256 firmado con `JWT_SECRET_KEY` | `tests/conftest.py:44-45` (`JWT_ALGORITHM`) | ⏳ |
| A3 | Claims del JWT: `sub` = id del usuario (str), `role`, `exp`. Si `sub` es el email, ajustar `_stub_token` | `tests/conftest.py:193` | ⏳ |
| A4 | **Stub de tokens activo** (`USE_STUB_TOKENS = True`). Poner a `False` cuando exista `/auth/login` y borrar `_stub_token` | `tests/conftest.py:41-43`, `:192` | ⏳ |
| A5 | `get_current_user()` y `require_role(*roles)` con la firma de §5.2. **Ojo:** mientras siga el stub que «devuelve un admin fijo», los tests de 403 para `waiter`/`customer` fallarán. Es lo esperado hasta el 06/10 | Router de mesas (Fase 2) y tests de integración | ⏳ |

## 5. Errores y paginación (Rita, R-04 / HU-11)

Todavía no los usa ningún fichero de la Fase 1. Se usarán en el servicio y el router (Fase 2).

| # | Firma asumida | Se usará en | Estado |
|---|---|---|---|
| E1 | `app.core.exceptions.NotFoundError` y `ConflictError`, con handler global que responde `{"detail": str, "code": str}` | `app/services/dining_table_service.py` | ⏳ (falta conocer el constructor y los valores de `code`) |
| P1 | Helper de `app.core.pagination` que devuelve `{"items", "total", "page", "size"}` | `GET /tables` | ⏳ (falta conocer el nombre, la firma y los límites de `size`) |

## 6. Herramientas y configuración

| # | Punto | Dónde | Estado |
|---|---|---|---|
| T1 | `# noqa: I001` temporal: mientras `app/core/` no exista, ruff clasifica `app.core` como paquete de terceros y pide otro orden de imports. Quitarlo cuando llegue el esqueleto | `app/models/dining_table.py:6-7` | ⏳ |
| T2 | No hay `pyproject.toml` ni `ruff.toml`: se ha usado la configuración por defecto de ruff (line-length 88) | Todos los ficheros nuevos | ⏳ (Carla y Anna) |
| T3 | Con solo `conftest.py` y sin tests, `pytest` sale con código 5 («no tests collected»). Se resuelve al añadir los tests de la Fase 2 | `deploy.yml` (paso de pytest) | ⏳ |
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
