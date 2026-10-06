#!/bin/sh
# Aplica las migraciones (si ya existe Alembic) y arranca la API.
set -e

if [ -f alembic.ini ]; then
  echo "Aplicando migraciones de Alembic..."
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" "$@"
