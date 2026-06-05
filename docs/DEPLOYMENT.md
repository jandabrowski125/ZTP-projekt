# Cloud deployment guide

EventRadar backend uses a **single public entry point** (`api` gateway) with internal microservices on a private Docker network.

## Architecture

```
Internet
   │
   ▼
Frontend (Cloudflare Pages) ──CORS──► api  (only public service)
                                        │
                          X-Internal-Service-Token
                                        ├──► events-service  (/internal/v1/*)
                                        └──► user-service    (/internal/v1/*) ──► PostgreSQL
```

**Step-by-step deploy (Hetzner VPS + Cloudflare Pages):** **[DEPLOYMENT_HETZNER.md](DEPLOYMENT_HETZNER.md)**.

| Environment | Compose file |
|-------------|--------------|
| Local dev | `docker compose up --build` → `docker-compose.yml` |
| Production (VPS) | `docker compose -f docker-compose.hetzner.yml up -d --build` |

## Security model

| Layer | Mechanism |
|-------|-----------|
| **Public API** | Only `api` is exposed. CORS allows explicit frontend origins. Rate limits on auth and general API. |
| **Internal services** | `/internal/v1/*` requires `X-Internal-Service-Token`. Returns 403 without it in production. |
| **Admin panels** | Swagger (`/docs`) protected by HTTP Basic auth (`DOCS_USERNAME` / `DOCS_PASSWORD`). |
| **User data** | JWT Bearer tokens (HS256), bcrypt passwords in user-service. |
| **Startup validation** | `APP_ENV=production` fails fast on weak JWT, internal token, CORS, docs password, or `TRUSTED_HOSTS=*`. |

## Required secrets (production)

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | `production` |
| `POSTGRES_PASSWORD` | Postgres container password (Hetzner stack) |
| `JWT_SECRET` | User session tokens (≥32 chars) |
| `INTERNAL_SERVICE_TOKEN` | Gateway → internal services (≥32 chars) |
| `DOCS_PASSWORD` | Swagger Basic auth (≥16 chars) |
| `CORS_ORIGINS` | Frontend origin, e.g. `https://app.pages.dev` |
| `TRUSTED_HOSTS` | API hostname, e.g. `api.example.com` |
| `TICKETMASTER_API_KEY` | Event provider |

## Frontend connection

The frontend calls `https://api.example.com/api/v1/...` via `VITE_API_URL` (Cloudflare Pages build env).

Authenticated requests: `Authorization: Bearer <accessToken>`.

## Health checks

| Service | Endpoint |
|---------|----------|
| api | `GET /health` |
| user-service | `GET /health` (503 if DB schema missing) |
| events-service | `GET /health` (internal only) |

## Rate limits (api gateway)

| Path | Limit |
|------|-------|
| `POST /api/v1/auth/register` | 5 / min / IP |
| `POST /api/v1/auth/login` | 10 / min / IP |
| `/docs`, `/openapi.json` | 20 / min / IP |
| Other `/api/v1/*` | 120 / min / IP |

## Local development

With `APP_ENV=development` (default in `docker-compose.yml`):

- Internal token optional when empty
- `/docs` open when `DOCS_PASSWORD` is empty
- CORS defaults to localhost Vite ports

## Checklist before go-live

- [ ] `APP_ENV=production`
- [ ] Strong `JWT_SECRET`, `INTERNAL_SERVICE_TOKEN`, `POSTGRES_PASSWORD`, `DOCS_PASSWORD`
- [ ] `CORS_ORIGINS` lists production frontend only
- [ ] `TRUSTED_HOSTS` set to API domain (not `*`)
- [ ] Postgres port **not** exposed to the internet
- [ ] Internal service ports not published on the host
- [ ] `/docs` requires password on public API
