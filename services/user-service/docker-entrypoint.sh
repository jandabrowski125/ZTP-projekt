#!/bin/sh
set -e
cd /app/services/user-service
alembic -c alembic.ini upgrade head
exec uvicorn user_app.main:app --host "${USER_SERVICE_HOST:-0.0.0.0}" --port "${USER_SERVICE_PORT:-8002}"
