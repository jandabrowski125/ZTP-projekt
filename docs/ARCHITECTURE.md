# EventRadar - dokumentacja architektury backendu

Backend monorepo (`ZTP-projekt`) dla aplikacji [EventRadar](../../Tpfeventradar/). Stack: **Python 3.12**, **FastAPI**, **Uvicorn**, **PostgreSQL 16**, **Docker Compose**.

Powiązane dokumenty:

| Dokument | Zawartość |
|----------|-----------|
| [README.md](../README.md) | Quick start, zmienne środowiskowe |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Model bezpieczeństwa produkcyjnego |
| [DEPLOYMENT_HETZNER.md](DEPLOYMENT_HETZNER.md) | Deploy: Hetzner VPS + Cloudflare (frontend) |
| [DATABASE.md](DATABASE.md) | Schemat PostgreSQL, migracje Alembic |

---

## 1. Przegląd systemu

Architektura opiera się na **mikroserwisach** w Dockerze. Z internetu dostępny jest wyłącznie **API Gateway**; pozostałe serwisy komunikują się po wewnętrznej sieci Compose.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Frontend (Cloudflare Workers / Vite dev)                               │
│  VITE_API_URL → https://api.example.com                                 │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTPS  /api/v1/*
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  api (gateway) :8000          - publiczny REST, CORS, rate limit, DTO    │
└───────┬─────────────────────────────────────────┬───────────────────────┘
        │ HTTP /internal/v1/*                     │ HTTP /internal/v1/*
        │ + X-Internal-Service-Token              │ + Authorization: Bearer
        ▼                                         ▼
┌───────────────────────────┐         ┌───────────────────────────────────┐
│  events-service :8001     │         │  user-service :8002               │
│  agregacja providerów     │         │  użytkownicy, ulubione, własne    │
│  (Ticketmaster, EB…)      │         │  wydarzenia → PostgreSQL          │
└───────────┬───────────────┘         └───────────────────┬───────────────┘
            │ HTTPS (zewnętrzne API)                        │
            ▼                                             ▼
   Ticketmaster Discovery API                    postgres :5432 (kontener)
   Eventbrite API v3
```

### Serwisy

| Serwis | Port | Ekspozycja | Odpowiedzialność |
|--------|------|------------|------------------|
| **api** | 8000 | Publiczny (prod: tylko `127.0.0.1` + Caddy) | Jedyny punkt wejścia dla frontendu; mapowanie snake_case → camelCase |
| **events-service** | 8001 | Tylko sieć Docker | Pobieranie i agregacja wydarzeń z API zewnętrznych |
| **user-service** | 8002 | Tylko sieć Docker | Auth (JWT), profile, ulubione, własne wydarzenia |
| **postgres** | 5432 | Dev: host; prod: bez portu na hoście | Persystencja użytkowników |

Wspólny pakiet **`eventradar_common`** (`services/common/`) - middleware bezpieczeństwa i walidacja produkcji, współdzielony przez wszystkie serwisy.

---

## 2. Kluczowe decyzje projektowe

Poniżej znajdują się najważniejsze decyzje projektowe.

### 2.1 Minimalna ekspozycja sieciowa

Tylko **gateway** jest publiczny. `events-service` i `user-service` nasłuchują na `expose` w Compose - frontend i świat zewnętrzny nie mają do nich bezpośredniego dostępu. Komunikacja między serwisami wymaga w produkcji nagłówka **`X-Internal-Service-Token`**.

### 2.2 Warstwy danych: domena → wewnętrzne schematy → publiczne DTO

| Warstwa | Lokalizacja | Konwencja |
|---------|-------------|-----------|
| Model domenowy | `events_app/domain/models.py` | Dataclassy Python (snake_case) |
| Kontrakt wewnętrzny | `events_app/schemas/internal.py` | JSON snake_case między serwisami |
| Kontrakt publiczny | `gateway/dto/` | Pydantic z aliasami **camelCase** dla React |
| Mapowanie | `gateway/mappers/`, `providers/*/mapper.py` | Jawne transformacje |

Gateway **nigdy** nie eksponuje modeli domenowych ani surowego JSON providerów - zmiana UI lub źródła danych nie wymaga przebudowy całego stosu.

### 2.3 Modularni providerzy zamiast jednego źródła

Zamiast jednej bazy wydarzeń system łączy **wiele zewnętrznych API** przez wzorzec **Strategy** + **Aggregator**:

- nowy provider = nowa klasa w `providers/` + rejestracja w `factory.py`;
- awaria jednego providera nie blokuje pozostałych (graceful degradation);
- mock (`MockEventRepository`) pozostaje do testów.

### 2.4 Identyfikatory wydarzeń

Zewnętrzne ID (np. string Ticketmaster) mapowane są na stabilne **`int`** dla frontendu:

```python
public_id = zlib.crc32(f"{provider}:{external_id}".encode()) & 0x7FFFFFFF
```

`EventIdRegistry` utrzymuje mapowanie `(provider, external_id) ↔ public_id` w ramach sesji wyszukiwania - umożliwia `GET /events/{id}` bez ponownego full-text search u providera.

### 2.5 Filtrowanie po stronie events-service

Parametry `category`, `location`, `date_from`, `date_to`, `query`, `sort`, `lat`, `lng` są przetwarzane w **repozytorium/agregatorze**, nie w gateway. Gateway pełni rolę cienkiego proxy + walidacji dat.

### 2.6 PostgreSQL dla użytkowników, providerzy dla katalogu wydarzeń

Katalog wydarzeń pochodzi z API zewnętrznych (Ticketmaster jako główne źródło). PostgreSQL przechowuje konta, ulubione, historię i **własne wydarzenia** dodawane przez organizatorów (venue).

### 2.7 Przygotowanie pod hosting chmurowy

- **`docker-compose.yml`** - development (Postgres na `5432`, API na `0.0.0.0:8000`);
- **`docker-compose.hetzner.yml`** - produkcja (Postgres bez publicznego portu, API na `127.0.0.1:8000`, Caddy + Let's Encrypt);
- **`APP_ENV=production`** - fail-fast przy słabych sekretach (`validate_production_settings`);
- frontend statyczny na **Cloudflare Workers**, backend na **Hetzner VPS** - patrz [DEPLOYMENT_HETZNER.md](DEPLOYMENT_HETZNER.md).

---

## 3. Wzorce projektowe (design patterns)

| Wzorzec | Implementacja | Cel |
|---------|---------------|-----|
| **API Gateway / BFF** | `services/api/gateway/` | Jeden publiczny punkt wejścia, CORS, limity, format JSON dla UI |
| **Backend for Frontend** | camelCase DTO, `EventFacade` | Kontrakt dopasowany do typów React (`EventData`, `MapPin`) |
| **Facade** | `gateway/services/event_facade.py` | Uproszczenie tras - orchestracja klienta HTTP + mapperów |
| **Repository** | `EventRepository` (Protocol), `UserRepository`, `CustomEventRepository` | Abstrakcja dostępu do danych |
| **Aggregator** | `AggregatorEventRepository` | Merge wielu providerów, deduplikacja, sortowanie |
| **Strategy** | `TicketmasterProvider`, `EventbriteProvider` | Wymienne źródła wydarzeń |
| **Factory** | `build_event_repository()` | Składanie providerów z konfiguracji `.env` |
| **Protocol (structural typing)** | `EventProvider`, `EventRepository` | Kontrakty bez dziedziczenia klas |
| **Mapper** | `providers/*/mapper.py`, `gateway/mappers/` | Izolacja formatów zewnętrznych od domeny |
| **Dependency Injection** | FastAPI `Depends()` | `get_facade`, `get_db`, `get_current_user` |
| **Middleware chain** | `main.py` w każdym serwisie | Cross-cutting: auth, rate limit, nagłówki bezpieczeństwa |

---

## 4. Integracja z providerami zewnętrznymi

### Ticketmaster Discovery API v2

- **Klient:** `events_app/providers/ticketmaster/client.py`
- **Endpoint:** `GET https://app.ticketmaster.com/discovery/v2/events.json`
- **Parametry:** `latlong`, `radius`, `unit` (km/miles), `countryCode`, `classificationName`, `keyword`, zakres dat
- **Cache:** pamięć in-process, TTL (`TICKETMASTER_CACHE_TTL_SECONDS`, domyślnie 60 s); przy HTTP 429 zwracane są stale wyniki
- **Mapowanie:** `mapper.py` - venue, ceny, lineup z `_embedded.attractions`, placeholder `"No data available"` dla brakujących pól

### Eventbrite API v3

- **Klient:** `events_app/providers/eventbrite/client.py`
- Publiczny endpoint **`/events/search/` został wycofany** (404/406) - wymagany **`EVENTBRITE_ORGANIZATION_ID`**
- Lista: `GET /organizations/{id}/events/` + filtr haversine po współrzędnych venue w promieniu `EVENTBRITE_RADIUS`
- Szczegóły: `GET /events/{id}/?expand=venue,category,...`

### Agregacja (`aggregator_repository.py`)

1. Wywołanie każdego providera po kolei;
2. przy błędzie - log + pominięcie (reszta providerów działa);
3. deduplikacja po `event.id`;
4. filtry po stronie klienta (kategoria, lokalizacja, tekst, daty);
5. sortowanie: `date_asc`, `date_desc`, `price_asc`.

---

## 5. Publiczne endpointy API

Prefix publiczny: **`/api/v1`**. Dokumentacja OpenAPI: `/docs` (HTTP Basic Auth gdy ustawiono `DOCS_PASSWORD`).

### Health

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| `GET` | `/health` | Status gateway: `{"status":"ok","service":"api"}` |

### Wydarzenia i mapa

| Metoda | Ścieżka | Query params | Opis |
|--------|---------|--------------|------|
| `GET` | `/api/v1/events` | `category`, `location`, `date_from`, `date_to`, `q`, `sort`, `lat`, `lng` | Lista wydarzeń `{ items, total }` |
| `GET` | `/api/v1/events/{event_id}` | - | Szczegóły (opis, lineup, bilety) |
| `GET` | `/api/v1/map/pins` | `category`, `location`, `date_from`, `date_to`, `lat`, `lng` | Pinezki mapy |
| `GET` | `/api/v1/categories` | - | Kategorie UI (chipy) |

**Sortowanie:** `date_asc` (domyślne), `date_desc`, `price_asc`.

**Walidacja dat:** `date_from` nie może być w przeszłości; `date_to >= date_from`.

### Autentykacja i profil

| Metoda | Ścieżka | Auth | Opis |
|--------|---------|------|------|
| `POST` | `/api/v1/auth/register` | - | Rejestracja → JWT (`accessToken` w camelCase) |
| `POST` | `/api/v1/auth/login` | - | Logowanie → JWT |
| `GET` | `/api/v1/users/me` | Bearer JWT | Profil zalogowanego użytkownika |
| `PATCH` | `/api/v1/users/me` | Bearer JWT | Aktualizacja profilu |

### Endpointy wewnętrzne (user-service) - jeszcze bez proxy w gateway

Zaimplementowane w `user-service`, niedostępne publicznie bez rozszerzenia gateway:

- ulubione: `GET/POST/DELETE .../users/me/favorites`
- minione wydarzenia: `GET/POST .../users/me/past-events`
- własne wydarzenia venue: `POST/GET .../custom-events`

---

## 6. Bezpieczeństwo

Pakiet `services/common/eventradar_common/`:

| Moduł | Funkcja |
|-------|---------|
| `internal_auth.py` | Ochrona `/internal/*` tokenem `X-Internal-Service-Token` |
| `docs_auth.py` | HTTP Basic na `/docs`, `/openapi.json` |
| `rate_limit.py` | Limit żądań per IP (uwzględnia `X-Forwarded-For` za Caddy) |
| `security_headers.py` | HSTS, `X-Frame-Options`, `Referrer-Policy`, … |
| `production.py` | Walidacja sekretów przy starcie (`APP_ENV=production`) |

**user-service:** bcrypt (hasła), JWT HS256 (tokeny dostępu, domyślnie 7 dni).

**Gateway (prod):** `TrustedHostMiddleware`, jawna lista `CORS_ORIGINS`, brak wildcardów.

Domyślne limity gateway (na IP):

| Ścieżka | Limit |
|---------|-------|
| `/api/v1/auth/register` | 5 / min |
| `/api/v1/auth/login` | 10 / min |
| `/docs`, `/openapi.json` | 20 / min |
| pozostałe | 120 / min |

Szczegóły: [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 7. Baza danych (user-service)

- **Silnik:** PostgreSQL 16 (kontener Docker)
- **ORM:** SQLAlchemy 2.x
- **Migracje:** Alembic (`services/user-service/alembic/`)
- **Bootstrap:** przy starcie kontenera `user_app.db.bootstrap` - upgrade schematu, weryfikacja tabel

Główne tabele:

| Tabela | Przeznaczenie |
|--------|---------------|
| `users` | Konto, hash hasła, profil, `preferences` (JSONB) |
| `user_saved_events` | Ulubione i minione wydarzenia (link do `public_event_id` + provider) |
| `custom_events` | Wydarzenia dodane przez organizatorów (geo, lineup, status) |

Pełny opis: [DATABASE.md](DATABASE.md).

---

## 8. Testy i TDD

Projekt stosuje **Test-Driven Design** w praktyce iteracyjnej: testy pisane równolegle z implementacją kontraktu API, repozytoriów i mapperów - przed i w trakcie integracji providerów.

### Narzędzia

- **pytest** + **pytest-asyncio** - monorepo, `pyproject.toml` → `testpaths` obejmuje 4 katalogi testów
- **ruff** - lint i format (`ruff check`, `ruff format`)
- **GitHub Actions** - `.github/workflows/pytest.yml` (Postgres 16 jako service)
- **Pre-commit** - `.pre-commit-config.yaml` + `.githooks/pre-commit` → `scripts/pre-commit-test.sh`

### Co jest testowane

| Obszar | Przykładowe pliki | Zakres |
|--------|-------------------|--------|
| Bezpieczeństwo | `services/common/tests/test_security.py` | Internal auth, docs auth, rate limit, walidacja prod |
| Gateway API | `services/api/tests/test_gateway_api.py` | Endpointy publiczne, camelCase, walidacja dat |
| Agregator | `services/events-service/tests/test_aggregator_repository.py` | Merge, deduplikacja, odporność na błąd providera |
| Ticketmaster | `test_ticketmaster_client.py`, `test_ticketmaster_mapper.py` | Cache, 429, mapowanie pól |
| Eventbrite | `test_eventbrite_client.py` | Org events, filtr geo, deprecated search |
| User-service | `test_api_routes.py`, `test_user_repository.py` | Auth, ulubione, schemat DB |

### Uruchomienie

```bash
pip install -e ".[dev]"
pytest
```

Testy integracyjne `user-service` wymagają PostgreSQL (`docker compose up -d postgres` lub `TEST_DATABASE_URL`).

Pre-commit uruchamia pytest dla `user-service`, `events-service` i `api`; przy braku lokalnych zależności fallback na Docker.

---

## 9. Struktura repozytorium

```
ZTP-projekt/
├── pyproject.toml              # zależności, pytest, ruff
├── docker-compose.yml          # dev
├── docker-compose.hetzner.yml  # produkcja VPS
├── .env.example
├── docs/                       # dokumentacja (ten plik + deploy + DB)
├── deploy/hetzner/Caddyfile    # reverse proxy HTTPS
└── services/
    ├── api/gateway/            # publiczny gateway
    ├── events-service/events_app/
    ├── user-service/user_app/
    └── common/eventradar_common/
```

---

## 10. Hosting i deployment

### Development

```bash
docker compose up --build
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Produkcja (Hetzner + Cloudflare)

| Komponent | Gdzie |
|-----------|--------|
| Frontend (Vite SPA) | Cloudflare Workers (`wrangler.toml`, build CI) |
| API Gateway | Hetzner VPS, Docker, port `127.0.0.1:8000` |
| Caddy | TLS termination, reverse proxy → API |
| PostgreSQL | Kontener na tym samym VPS |
| DNS | Cloudflare (`api.*` → A record VPS, apex → Worker) |

Wymagane zmienne produkcyjne: `POSTGRES_PASSWORD`, `JWT_SECRET`, `INTERNAL_SERVICE_TOKEN`, `DOCS_PASSWORD`, `CORS_ORIGINS`, `TRUSTED_HOSTS`, `TICKETMASTER_API_KEY`.

Checklist bezpieczeństwa i krok po kroku: [DEPLOYMENT_HETZNER.md](DEPLOYMENT_HETZNER.md), [DEPLOYMENT.md](DEPLOYMENT.md).

### Healthchecki Compose

Serwis `api` startuje dopiero po `healthy` dla `events-service` i `user-service` - unika błędów połączenia przy `docker compose up`.

---

## 11. Integracja z frontendem

- Base URL: zmienna **`VITE_API_URL`** (np. `https://api.eventradar.net.pl`)
- Frontend woła **`{VITE_API_URL}/api/v1/...`**
- JSON w **camelCase** - zgodność z typami w `Tpfeventradar/frontend/src/app/api/types.ts`
- Dev: Vite proxy `/api` → `localhost:8000` gdy `VITE_API_URL` puste

---

## 12. Licencja

Projekt na licencji [AGPL-3.0-or-later](https://www.gnu.org/licenses/agpl-3.0.html).
