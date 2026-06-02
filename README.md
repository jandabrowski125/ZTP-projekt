# EventRadar Backend

Backend REST API for [EventRadar](../Tpfeventradar/) (FastAPI + Uvicorn), designed to replace frontend mock data.

## Architecture

| Service | Port (host) | Exposure | Role |
|---------|-------------|----------|------|
| **api** | `8000` | Public | REST API for the frontend (`/api/v1/*`), CORS, camelCase DTOs |
| **events-service** | — (internal `8001`) | Docker network only | Aggregates external providers (Ticketmaster, …) |

```
Frontend  →  api:8000  →  events-service:8001  →  Aggregator → Ticketmaster Discovery API
```

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

- Public API: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

`events-service` is not published on the host — only `api` is reachable from the frontend.

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
| `GET /api/v1/map/pins` | Map pins (`MapPin` shape) |
| `GET /api/v1/categories` | Category chips |

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
| `TICKETMASTER_API_KEY` | events-service | *(required)* |
| `DEFAULT_COORD_LAT` / `DEFAULT_COORD_LNG` | events-service | Kraków (50.046943, 19.997153) |
| `TICKETMASTER_LAT` / `TICKETMASTER_LNG` | events-service | inherit `DEFAULT_COORD_*` |
| `TICKETMASTER_RADIUS` | events-service | `50` |
| `TICKETMASTER_UNIT` | events-service | `km` or `miles` (API rejects `kilometers`) |
| `TICKETMASTER_COUNTRY_CODE` | events-service | `PL` — omit (empty) for global search; not related to HTTP 429 |
| `TICKETMASTER_CACHE_TTL_SECONDS` | events-service | `60` — caches TM search; avoids 429 when `/events` and `/map/pins` run together |
| `EVENTS_SERVICE_URL` | api | `http://events-service:8001` |
| `CORS_ORIGINS` | api | `http://localhost:5173,http://localhost:5678,...` |
| `API_PORT` | api | `8000` |

See `eventradar_architectural_decisions.txt` in the parent folder for design rationale.
