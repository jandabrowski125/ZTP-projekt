#!/bin/sh
set -eu

DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-eventradar}
DB_NAME=${DB_NAME:-eventradar}

# wait for postgres
MAX_WAIT=60
WAITED=0
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
  WAITED=$((WAITED+1))
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "Postgres unreachable after ${MAX_WAIT}s"
    exit 1
  fi
  echo "Waiting for Postgres... ($WAITED/$MAX_WAIT)"
  sleep 1
done

# run alembic with a few retries
MIGRATION_RETRIES=3
i=0
until alembic -c /app/services/user-service/alembic.ini upgrade head; do
  i=$((i+1))
  echo "alembic failed (attempt $i/$MIGRATION_RETRIES)"
  if [ "$i" -ge "$MIGRATION_RETRIES" ]; then
    echo "Migrations failed permanently"
    exit 1
  fi
  sleep $((5 * i))
done

# start the app
exec uvicorn user_app.main:app --host 0.0.0.0 --port 8002
