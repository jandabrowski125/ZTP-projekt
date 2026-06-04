#!/usr/bin/env sh
# Run backend tests before commit. Uses local pytest when deps+Postgres are available,
# otherwise runs the user-service test suite in Docker.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

run_local() {
  python -m pytest -q \
    services/user-service/tests \
    services/events-service/tests \
    services/api/tests
}

run_docker() {
  if docker compose ps --status running user-service 2>/dev/null | grep -q user-service; then
    docker compose exec -T user-service sh -c 'pip install -q pytest && python -m pytest -q tests'
  else
    docker compose run --rm --no-deps user-service \
      sh -c 'pip install -q pytest && python -m pytest -q tests'
  fi
}

if python -c "import pytest, psycopg" 2>/dev/null; then
  if run_local; then
    exit 0
  fi
  echo "Local pytest failed; trying Docker..."
fi

if command -v docker >/dev/null 2>&1; then
  run_docker
  exit 0
fi

echo "Install dev deps (pip install -e \".[dev]\") and ensure PostgreSQL is running, or start Docker."
exit 1
