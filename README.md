# 🍽️ RestoAPI — Backend

API REST para la gestión de un restaurante: usuarios y roles, mesas, reservas, menú, pedidos, cocina en tiempo real, facturación, estadísticas y notificaciones por email.

> Frontend: [IA-P1-BCN/Resto-API_Frontend](https://github.com/IA-P1-BCN/Resto-API_Frontend)

## Stack

| Capa | Tecnología |
|---|---|
| API | FastAPI + Uvicorn |
| ORM y migraciones | SQLAlchemy 2 + Alembic |
| Base de datos | PostgreSQL (Neon en producción, Docker en local) |
| Validación y config | Pydantic v2 + pydantic-settings |
| Auth | JWT (PyJWT) + bcrypt |
| Email | Brevo (vía httpx) |
| Caché | cachetools |
| Tests y calidad | pytest + pytest-cov + httpx · ruff |

## Puesta en marcha

Requisitos: **Python 3.12** y **Git**.

```bash
# 1. Clonar y situarse en dev
git clone https://github.com/IA-P1-BCN/Resto-API_Backend.git
cd Resto-API_Backend
git switch dev

# 2. Entorno virtual
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (Git Bash):    source .venv/Scripts/activate
# macOS / Linux:         source .venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
cp .env.example .env    # y rellenar los valores
```

## Flujo de trabajo (Gitflow)

| Rama | Uso | Commits directos |
|---|---|---|
| `main` | Producción (Render + Neon `main`) | ❌ Nunca |
| `dev` | Integración, rama por defecto | ❌ Nunca |
| `feature/HU-XX-descripcion` | Una rama por HU, sale de `dev` | ✅ Solo su dueña/o |
| `fix/HU-XX-descripcion` | Bug detectado en `dev` | ✅ Solo su dueña/o |
| `hotfix/descripcion` | Urgencia en producción, sale de `main` | ✅ Solo su dueña/o |

```bash
# Empezar una HU
git switch dev
git pull origin dev
git switch -c feature/HU-07-crear-pedido

# Antes de abrir el PR
git pull origin dev     # traer lo último de dev y resolver conflictos en TU rama
pytest
git push -u origin feature/HU-07-crear-pedido
```

1. PR **`feature/...` → `dev`** con título `[HU-XX] Descripción` y `Closes #N`.
2. Lo revisa, aprueba y mergea **otra persona** (*Squash and merge*). La rama se borra automáticamente.
3. Quien mergea avisa en el canal: `✅ Mergeado #N [HU-XX] en dev → ¡haced pull!`
4. Todo el equipo actualiza su rama: `git pull origin dev`.
5. Al cierre de cada sprint: PR `dev` → `main` (*merge commit*) → despliegue.

**Commits** — [Conventional Commits](https://www.conventionalcommits.org/es/):
`feat(pedidos): ...` · `fix(reservas): ...` · `test(auth): ...` · `docs(api): ...` · `ci: ...` · `chore(deps): ...`

## Reglas

- `.env` nunca se sube; solo `.env.example` sin valores reales.
- Una sola persona (Carla) mergea migraciones de Alembic en `dev`, de una en una.
- PRs pequeños (idealmente < 400 líneas).
