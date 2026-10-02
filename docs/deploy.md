# 🚀 Guía de despliegue — RestoAPI

> **Solo Anna despliega.** Únicamente ella puede mergear en `main` y tiene acceso a Neon, Render y Vercel.

| Pieza | Plataforma | Repo | Se despliega cuando… |
|---|---|---|---|
| Base de datos | Neon (PostgreSQL 16) | — | Migraciones con `alembic upgrade head` en el arranque de Render |
| API | Render (Web Service, free) | `Resto-API_Backend` | Push a `main` → `deploy.yml` → tests en verde → deploy hook |
| Web | Vercel (Hobby) | `Resto-API_Frontend` | Push a `main` (producción) · cada PR genera una Preview URL |

## 1. Neon (base de datos)

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

> El primer deploy fallará hasta que exista `app/main.py` (esqueleto de Carla, C-01) y `alembic.ini`. Es normal.

## 3. GitHub Actions (repo Backend)

**Settings → Secrets and variables → Actions:**

| Tipo | Nombre | Valor |
|---|---|---|
| Secret | `RENDER_DEPLOY_HOOK_URL` | URL del deploy hook de Render |
| Secret | `JWT_SECRET_KEY_TEST` | Cualquier cadena (solo tests) |
| Variable | `RENDER_URL` | `https://<servicio>.onrender.com` |
| Variable | `COVERAGE_MIN` | `0` al principio · `70` en el Sprint 2 |

Mientras `RENDER_DEPLOY_HOOK_URL` no exista, `deploy.yml` ejecuta los tests y **omite** el deploy con un aviso.
Los pasos de Alembic, pytest y Docker se activan solos cuando existan `alembic.ini`, `tests/` y `Dockerfile`.

Lanzar un deploy a mano: **Actions → deploy → Run workflow** (rama `main`).

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

1. Vercel despliega el frontend automáticamente.
2. `deploy.yml` ejecuta los tests y, si pasan, despliega la API en Render y comprueba `/health`.
3. Verificar: `<RENDER_URL>/health`, `<RENDER_URL>/docs` y la web en Vercel.

## 6. Checklist antes de la demo (D10)

- [ ] Abrir `<RENDER_URL>/health` 5-10 min antes (cold start del free tier ≈ 50 s)
- [ ] Datos de demo cargados en Neon `main`
- [ ] Usuarios demo por rol funcionando
- [ ] Vídeo de respaldo grabado (D9) y `docker-compose up` listo como plan B
