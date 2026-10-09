# 🚀 Guía de despliegue — RestoAPI

> **Solo Anna despliega.** Únicamente ella puede mergear en `main` y tiene acceso a Neon, Render y Vercel.

| Pieza | Plataforma | Repo | Se despliega cuando… |
|---|---|---|---|
| Base de datos | Neon (PostgreSQL 16) | — | Migraciones con `alembic upgrade head` en el arranque de Render |
| API | Render (Web Service, free) | `Resto-API_Backend` | Push a `main` → `deploy.yml` → tests en verde → deploy hook |
| Web | Vercel (Hobby) | `Resto-API_Frontend` | Push a `main` (producción) · cada PR genera una Preview URL |

## 1. Neon (base de datos)

> ✅ **Ya creado** (2026-10-02): proyecto `Resto-API` (`small-violet-45321750`) en la organización de Anna · AWS Frankfurt · Postgres 16 · base de datos `restoapi`.
>
> | Rama Neon | Usuario | Uso | Quién tiene la URL |
> |---|---|---|---|
> | `main` | `restoapi_owner` | Producción (Render) | Solo Anna |
> | `dev` | `restoapi_dev` | Integración compartida | Equipo |
>
> `restoapi_dev` solo existe en la rama `dev`: compartir su URL no da acceso a producción.
> **Nunca** compartas la URL de `restoapi_owner`: tiene la misma contraseña en `main` y en `dev`.

Pasos (por si hay que recrearlo):

1. [neon.tech](https://neon.tech) → **New Project** → región **AWS Europe (Frankfurt)** · Postgres 16 · base de datos `restoapi`.
2. **Branches → New branch** `dev` desde `main` (`main` = producción, `dev` = integración).
3. **Connect** → marcar *Connection pooling* → copiar la cadena y adaptarla a SQLAlchemy:
   ```
   postgresql+psycopg://USER:PASS@HOST-pooler.REGION.aws.neon.tech/restoapi?sslmode=require
   ```
4. Guardar las dos URLs (rama `main` y rama `dev`) en un gestor de secretos. Nunca en el chat ni en el repo.

## 2. Render (API)

1. Render → **New → Blueprint** → repo `IA-P1-BCN/Resto-API_Backend` (lee [`render.yaml`](../render.yaml)).
2. Rellenar las variables marcadas como `sync: false`:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | Neon, rama `main` (pooled) |
   | `ALLOWED_ORIGINS` | URL de producción de Vercel (p. ej. `https://restoapi.vercel.app`) |
   | `BREVO_API_KEY`, `MAIL_FROM` | Vacías hasta HU-19 (D7) |

   `JWT_SECRET_KEY` la genera Render automáticamente.
3. **Settings → Deploy Hook** → copiar la URL.
4. Comprobar que **Auto-Deploy está en Off** (el deploy lo lanza GitHub Actions).
5. Cuando exista `/health` (D3): abrir `https://<servicio>.onrender.com/docs`.

> El arranque (`sh docker-entrypoint.sh`) aplica `alembic upgrade head` solo si existe `alembic.ini`, así que la API ya se puede desplegar antes de tener migraciones.

## 3. GitHub Actions (repo Backend)

**Settings → Secrets and variables → Actions:**

| Tipo | Nombre | Valor |
|---|---|---|
| Secret | `RENDER_DEPLOY_HOOK_URL` | URL del deploy hook de Render |
| Secret | `JWT_SECRET_KEY_TEST` | Cualquier cadena (solo tests) |
| Variable | `RENDER_URL` | `https://<servicio>.onrender.com` |
| Variable | `COVERAGE_MIN` | `0` al principio · `70` en el Sprint 2 |

| Workflow | Cuándo | Qué hace |
|---|---|---|
| `ci.yml` (job `tests`) | PR a `dev`/`main` y push a `dev` | ruff → una sola cabeza de Alembic → migraciones → pytest + cobertura → build Docker. Check obligatorio para mergear |
| `deploy.yml` | Push a `main` | Reutiliza `ci.yml` y, si pasa, dispara el deploy hook de Render y espera a que `/health` devuelva el commit desplegado (máx. 10 min) |

Mientras `RENDER_DEPLOY_HOOK_URL` no exista, `deploy.yml` ejecuta los tests y **omite** el deploy con un aviso.
Los pasos de Alembic, pytest y Docker se activan solos cuando existan `alembic.ini`, `tests/` y `Dockerfile`.

Lanzar un deploy a mano: **Actions → deploy → Run workflow** (rama `main`).

### Merge bloqueado si el CI falla

El check del CI es obligatorio en `dev` y `main` de los dos repos (ruleset **CI obligatorio**: `tests` en el backend, `build` en el frontend). Con un test fallando el botón de merge queda bloqueado.

Se configura con [`scripts/github-rulesets.sh`](../scripts/github-rulesets.sh) (Anna, permisos de admin). Se puede volver a ejecutar sin problema: actualiza el ruleset si ya existe.

```bash
sh scripts/github-rulesets.sh
```

Para comprobar que funciona: **Settings → Rules → Rulesets** en cada repo, o abrir un PR con un test roto y ver el merge bloqueado.

## 4. Vercel (web)

1. Vercel → **Add New → Project** → importar `IA-P1-BCN/Resto-API_Frontend`.
2. Configuración:

   | Campo | Valor |
   |---|---|
   | Root Directory | `./` (raíz del repo) |
   | Framework Preset | Vite |
   | Build Command | `npm run build` |
   | Output Directory | `dist` |
   | Install Command | `npm ci` |
   | Env var | `VITE_API_URL` = URL de Render (Production y Preview) |

3. **Settings → Git → Production Branch** = `main`.
4. Añadir la URL de producción de Vercel a `ALLOWED_ORIGINS` en Render.

`vercel.json` ya incluye el *rewrite* para que las rutas del SPA no den 404.

## 5. Paso a producción (D5 y D9)

```bash
# Anna abre el PR dev → main en GitHub; otra persona lo aprueba; Anna mergea (merge commit, no squash)
# Después, sincronizar dev con main:
git switch dev && git pull
git merge origin/main
git push
```

1. Vercel despliega el frontend automáticamente (el CI del frontend ya ha pasado lint, tests y build en el PR).
2. `deploy.yml` ejecuta los tests y, si pasan, despliega la API en Render y comprueba `/health`.
3. Verificar: `<RENDER_URL>/health`, `<RENDER_URL>/docs` y la web en Vercel.

## 6. Checklist antes de la demo (D10)

- [ ] Abrir `<RENDER_URL>/health` 5-10 min antes (cold start del free tier ≈ 50 s)
- [ ] Datos de demo cargados en Neon `main`
- [ ] Usuarios demo por rol funcionando
- [ ] Vídeo de respaldo grabado (D9) y `docker-compose up` listo como plan B

## 7. Docker en local (HU-02)

Levanta todo el stack con un solo comando: API + PostgreSQL 16 + frontend. Sirve también como **plan B de la demo** si Render o Vercel fallan.

**Requisitos:** Docker Desktop arrancado y los dos repos clonados en la misma carpeta:

```text
P2_Resto/
├── Resto-API_Backend/    ← docker-compose.yml
└── Resto-API_Frontend/
```

Si el frontend está en otra ruta, añadir `FRONTEND_PATH=/ruta/al/frontend` en el `.env` del backend.

```bash
cd Resto-API_Backend
docker compose up --build        # primera vez o tras cambiar dependencias
docker compose up -d             # en segundo plano
docker compose logs -f api       # ver logs de la API
docker compose down              # parar
docker compose down -v           # parar y BORRAR los datos de la BD
```

| Servicio | URL | Imagen |
|---|---|---|
| `frontend` | http://localhost:5173 | `Resto-API_Frontend/Dockerfile` (Node 22 → nginx) |
| `api` | http://localhost:8000 · `/docs` | `Resto-API_Backend/Dockerfile` (Python 3.12) |
| `db` | `localhost:5432` (usuario, contraseña y BD: `restoapi`) | `postgres:16` |

- Al arrancar, la API aplica las migraciones (`alembic upgrade head`) si ya existe `alembic.ini`.
- `VITE_API_URL` se fija en el build del frontend: si cambia, hay que reconstruir con `docker compose up --build`.
- Si el puerto 5432 está ocupado (otro Postgres instalado en el equipo), añadir `DB_PORT=5433` al `.env`: la BD queda en `localhost:5433`.
- Login: `POST /auth/login` como formulario OAuth2 (`username` = email, `password`) devuelve `{access_token, token_type}`. En Swagger (`/docs`), el botón **Authorize** hace el login y añade el token a las peticiones.
- Para levantar el frontend sin API se puede usar datos simulados: `VITE_USE_MOCK=true` en el `.env` y `docker compose up --build`.
- Primer admin (sin él nadie puede usar `/users`): `docker compose exec api python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]`. Si el email ya existe, lo convierte en admin.
- Mientras no haya Alembic, las tablas se crean con `create_all`, que no añade columnas nuevas a tablas existentes: si una BD local es anterior a HU-05 (sin `users.role`), recrearla con `docker compose down -v`.
