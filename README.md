# EventRadar Backend

Backend REST API for [EventRadar](../Tpfeventradar/) (FastAPI + Uvicorn), designed to replace frontend mock data.

## Architecture

Pełna dokumentacja: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** (wzorce, decyzje, endpointy, TDD, hosting).

| Service | Port (host) | Exposure | Role |
|---------|-------------|----------|------|
| **api** | `8000` | Public | REST API for the frontend (`/api/v1/*`), CORS, camelCase DTOs |
| **events-service** | — (internal `8001`) | Docker network only | Aggregates external providers (Ticketmaster) |
| **user-service** | — (internal `8002`) | Docker network only | Users, favorites, past events, custom venue events (PostgreSQL) |
| **postgres** | `5432` (local dev only) | Dev: host port | PostgreSQL 16 — container on VPS in production (`docker-compose.hetzner.yml`) |

```
Frontend  →  api:8000  →  events-service:8001  →  Aggregator → Ticketmaster API
                       →  user-service:8002   →  PostgreSQL (Docker container)
```

### Database milestone

- **Engine:** PostgreSQL (relational users + favorites; JSONB for preferences/lineup).
- **Production:** Postgres container on Hetzner VPS (`docker-compose.hetzner.yml`). Local dev: `docker compose up` includes `postgres`.
- **Migrations:** `user_app.db.bootstrap` on `user-service` container start (Alembic).
- Full schema and rationale: **[docs/DATABASE.md](docs/DATABASE.md)**.

## Prerequisites

- Docker & Docker Compose
- (Optional, local dev) Python 3.12+

## Configuration (`.env`)

1. Copy `.env.example` → `.env`.
2. Set `TICKETMASTER_API_KEY` from [Ticketmaster Developer Portal](https://developer.ticketmaster.com/).
3. Default search/map center (Kraków, Rynek Główny):

```env
DEFAULT_COORD_LAT=50.046943
DEFAULT_COORD_LNG=19.997153
```

Provider-specific coordinates inherit from `DEFAULT_COORD_*` when `TICKETMASTER_LAT` / `TICKETMASTER_LNG` are omitted. The public API accepts optional `lat` & `lng` query params for map-based search.

## Quick start (Docker)

From this directory (`ZTP-projekt/`):

```bash
docker compose up --build
```

- Public API: http://localhost:8000/docs (HTTP Basic auth when `DOCS_PASSWORD` is set)  
- Health: http://localhost:8000/health  

`events-service` is not published on the host — only `api` is reachable from the frontend.

### Deployment

| Environment | Command |
|-------------|---------|
| **Local** | `docker compose up --build` |
| **Production** | [docs/DEPLOYMENT_HETZNER.md](docs/DEPLOYMENT_HETZNER.md) — Hetzner VPS + Cloudflare Pages |

Security model and env vars: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Local development (without Docker)

Terminal 1 — events service:

```bash
cd services/events-service
pip install -e "../../.[dev]"
$env:PYTHONPATH = "."   # PowerShell
uvicorn events_app.main:app --reload --port 8001
```

Terminal 2 — API gateway:

```bash
cd services/api
$env:PYTHONPATH = "."
$env:EVENTS_SERVICE_URL = "http://localhost:8001"
uvicorn gateway.main:app --reload --port 8000
```

## Frontend integration

Set the API base URL in the frontend (e.g. `VITE_API_URL=http://localhost:8000`).

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/events` | List events (`category`, `location`, `date_from`, `date_to`, `q`, `sort`, `lat`, `lng`) |
| `GET /api/v1/events/{id}` | Event details (+ `description`, `lineup`, `tickets`) |
| `GET /api/v1/map/pins` | Map pins (`category`, `location`, `date_from`, `date_to`, `lat`, `lng`) |
| `GET /api/v1/categories` | Category chips |
| `POST /api/v1/auth/register` | Create account (email, password, profile) |
| `POST /api/v1/auth/login` | JWT access token |
| `GET /api/v1/users/me` | Current user profile (`Authorization: Bearer …`) |

JSON uses **camelCase** fields aligned with `EventData` in `Tpfeventradar/frontend/src/app/components/dashboard/events.ts`.

Example:

```bash
curl "http://localhost:8000/api/v1/events?category=Music"
```

List response:

```json
{
  "items": [{ "id": 1, "shortTitle": "Electric Nights", ... }],
  "total": 2
}
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

User-service integration tests need PostgreSQL (`docker compose up -d postgres` or set `TEST_DATABASE_URL`). Security tests run without a database.

## Linting

```bash
ruff check services/
ruff format --check services/
```

Auto-fix:

```bash
ruff check services/ --fix
ruff format services/
```

## Environment variables

| Variable | Service | Default |
|----------|---------|---------|
| `TICKETMASTER_API_KEY` | events-service | Ticketmaster Discovery (required) |
| `DEFAULT_COORD_LAT` / `DEFAULT_COORD_LNG` | events-service | Kraków (50.046943, 19.997153) |
| `TICKETMASTER_LAT` / `TICKETMASTER_LNG` | events-service | inherit `DEFAULT_COORD_*` |
| `TICKETMASTER_RADIUS` | events-service | `50` |
| `TICKETMASTER_UNIT` | events-service | `km` or `miles` (API rejects `kilometers`) |
| `TICKETMASTER_COUNTRY_CODE` | events-service | `PL` — omit (empty) for global search; not related to HTTP 429 |
| `TICKETMASTER_CACHE_TTL_SECONDS` | events-service | `60` — caches TM search; avoids 429 when `/events` and `/map/pins` run together |
| `DATABASE_URL` | user-service | PostgreSQL connection URL (cloud in prod) |
| `JWT_SECRET` | user-service | Signing key for access tokens — **change in production** |
| `USER_SERVICE_URL` | api | `http://user-service:8002` |
| `EVENTS_SERVICE_URL` | api | `http://events-service:8001` |
| `CORS_ORIGINS` | api | `http://localhost:5173,http://localhost:5678,...` |
| `API_PORT` | api | `8000` |

See `eventradar_architectural_decisions.txt` in the parent folder for design rationale.

## License

This project is licensed under the [AGPL-3.0-or-later](https://www.gnu.org/licenses/agpl-3.0.html).

[![License: AGPLv3](https://www.gnu.org/graphics/agplv3-with-text-162x68.png)](https://www.gnu.org/licenses/agpl-3.0.html)
