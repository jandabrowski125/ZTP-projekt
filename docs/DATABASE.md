# EventRadar — database milestone

## Engine choice: **PostgreSQL**

| Criterion | PostgreSQL | MongoDB |
|-----------|------------|---------|
| Users + credentials | Strong (unique constraints, transactions) | Weaker for relational integrity |
| Favorites / past events (M:N) | Natural junction tables | Extra modeling |
| Custom venue events + FK to owner | `UUID` FK, indexes | Embedded docs possible but joins harder |
| Lineup / tickets / preferences | `JSONB` where needed | Native documents |
| Managed cloud (Neon, RDS, Supabase, Cloud SQL) | Mature, standard | Available |
| Team / SQL tooling | Alembic migrations, familiar ops | Different ops model |

**Decision:** PostgreSQL 16+ as the system of record. MongoDB would fit only if the product were document-only with no relational user↔event links; EventRadar needs both.

## Cloud-first deployment

- **Production (Hetzner):** PostgreSQL runs as a **Docker container on the same VPS** (`docker-compose.hetzner.yml`). Set `POSTGRES_PASSWORD` in `.env`; port 5432 is not published publicly.
- **Backend:** `user-service` connects via `DATABASE_URL` (12-factor). On Hetzner compose the URL is assembled automatically from `POSTGRES_*` vars.
- **Local dev:** `docker compose up` starts `postgres` alongside app services (`docker-compose.yml`).

## Containerization

| Component | Containerize? | Notes |
|-----------|---------------|--------|
| PostgreSQL (prod) | **Yes** (VPS) | Same host as API via `docker-compose.hetzner.yml` |
| PostgreSQL (local) | **Yes** | Included in `docker-compose.yml` |
| `user-service` | **Yes** | Same pattern as `events-service` / `api` |
| Migrations | **On startup** | `user_app.db.bootstrap` before uvicorn |

## Schema overview

### `users` (login + profile in one table)

Aligned with profile/register UI: `email`, `password_hash`, `username`, `full_name`, `bio`, `location`, `avatar_url`, `preferences` (JSONB: notifications, privacy), timestamps.

### `user_saved_events` (favorites + past)

- `list_type`: `favorite` | `past`
- Links to aggregated events (`public_event_id`, `provider`, `external_id`) or `custom_event_id`
- Optional `event_snapshot` (JSONB) for stable UI if provider data disappears
- `attended_at` for past events

### `custom_events` (venue-submitted, future feature)

Core fields matching provider `Event` / Add Event form: title, description, venue, location, `lat`/`lng`, category, price label, image URL, tags, `starts_at`/`ends_at`, status (`draft`|`published`|`cancelled`), optional `lineup`/`tickets` JSONB, `owner_user_id`.

## Connection

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

Run migrations:

```bash
cd ZTP-projekt
alembic -c services/user-service/alembic.ini upgrade head
```
