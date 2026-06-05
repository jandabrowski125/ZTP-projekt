# Deploy na Hetzner Cloud + Cloudflare Pages

Tani setup na projekt studencki / demo (bez realnego ruchu):

| Część | Gdzie | Koszt orientacyjny |
|-------|--------|-------------------|
| **Backend** (Docker) | [Hetzner Cloud Cost-Optimized](https://www.hetzner.com/cloud/cost-optimized) CX23 / CAX11 (2 vCPU, 4 GB) | ~3–4 €/mies. |
| **PostgreSQL** | Kontener na tej samej VM | w cenie VPS |
| **Frontend** (statyczny build Vite) | [Cloudflare Pages](https://pages.cloudflare.com/) | 0 € |
| **SSL API** | Caddy + Let's Encrypt na VPS | 0 € |

```
Użytkownik
    │
    ├─► https://app.pages.dev  (Cloudflare Pages — React)
    │         │
    │         └── fetch ──► https://api.twoja-domena.pl/api/v1/...
    │
    └─► Hetzner VPS
            Caddy :443 ──► api :8000 (localhost)
            Docker: api, events-service, user-service, postgres
```

---

## 1. Hetzner Cloud — utwórz serwer

1. Załóż konto w [Hetzner Console](https://console.hetzner.cloud/).
2. **Add Server** → typ **Cost-Optimized** (np. **CX23** lub **CAX11**).
3. Lokalizacja: **Falkenstein (fsn1)** lub **Nuremberg (nbg1)** — bliżej PL.
4. Image: **Ubuntu 24.04**.
5. Networking: publiczny IPv4 wystarczy.
6. SSH key — dodaj swój klucz (bez hasła root w produkcji).
7. Firewall (w konsoli Hetzner lub na serwerze):
   - **22** (SSH) — tylko Twój IP, jeśli możesz
   - **80**, **443** (HTTP/HTTPS dla Caddy)
   - **nie** otwieraj 5432, 8000, 8001, 8002 na świat

---

## 2. Przygotuj serwer (SSH)

```bash
ssh root@TWÓJ_IP

apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2 git caddy

systemctl enable --now docker
```

Opcjonalnie użytkownik bez roota:

```bash
adduser deploy
usermod -aG docker deploy
```

---

## 3. Backend — sklonuj repo i `.env`

```bash
cd /opt
git clone https://github.com/TWOJ_ORG/ZTP-projekt.git eventradar
cd eventradar

cp .env.example .env
nano .env
```

### Wygeneruj sekrety (lokalnie lub na serwerze)

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Uruchom 3× — dla `JWT_SECRET`, `INTERNAL_SERVICE_TOKEN`, `POSTGRES_PASSWORD`.

### Przykładowy `.env` produkcyjny

```env
APP_ENV=production

# Postgres (kontener na VPS — NIE wystawiaj portu 5432)
POSTGRES_USER=eventradar
POSTGRES_PASSWORD=<wygenerowane-48-znaków>
POSTGRES_DB=eventradar

JWT_SECRET=<wygenerowane-48-znaków>
INTERNAL_SERVICE_TOKEN=<wygenerowane-48-znaków>

DOCS_USERNAME=admin
DOCS_PASSWORD=<min-16-znaków>

# Po deployu frontu na Pages — dokładny origin (bez końcowego /)
CORS_ORIGINS=https://eventradar.pages.dev
TRUSTED_HOSTS=api.twoja-domena.pl

TRUST_PROXY_HEADERS=1

TICKETMASTER_API_KEY=<twój_klucz>
# opcjonalnie Eventbrite:
# EVENTBRITE_TOKEN=
# EVENTBRITE_ORGANIZATION_ID=
```

### Uruchom stack

```bash
docker compose -f docker-compose.hetzner.yml up -d --build
docker compose -f docker-compose.hetzner.yml ps
curl -s http://127.0.0.1:8000/health
```

`api` nasłuchuje tylko na **127.0.0.1:8000** — z zewnątrz nie widać go bez reverse proxy.

---

## 4. Caddy — publiczne HTTPS API

1. DNS: rekord **A** `api.twoja-domena.pl` → IP VPS (u dowolnego DNS; może być Cloudflare).
2. Skopiuj szablon:

```bash
cp deploy/hetzner/Caddyfile /etc/caddy/Caddyfile
nano /etc/caddy/Caddyfile   # zamień api.example.com
systemctl reload caddy
```

3. Sprawdź:

```bash
curl -s https://api.twoja-domena.pl/health
```

**Cloudflare proxy (pomarańczowa chmura):** ustaw SSL na **Full (strict)** i upewnij się, że origin ma ważny cert (Caddy/Let's Encrypt). Przy problemach na start użyj DNS-only (szara chmura) dla `api.*`.

---

## 5. Cloudflare Pages — frontend

Repo: **Tpfeventradar** (osobne od backendu).

### W Cloudflare Dashboard

1. **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Wybierz repo `Tpfeventradar`.
3. Ustawienia buildu:

| Pole | Wartość |
|------|---------|
| Root directory | `frontend` |
| Build command | `bun install && bun run build` *(lub `npm ci && npm run build`)* |
| Build output | `dist` |

4. **Environment variables** (Production):

| Zmienna | Wartość |
|---------|---------|
| `VITE_API_URL` | `https://api.twoja-domena.pl` |
| `VITE_DEFAULT_COORD_LAT` | `50.046943` |
| `VITE_DEFAULT_COORD_LNG` | `19.997153` |

5. Deploy.

Frontend woła API pod `VITE_API_URL/api/v1/...` (patrz `frontend/src/app/api/config.ts`).

### SPA routing

Plik `frontend/public/_redirects` (`/* /index.html 200`) trafia do `dist/` i naprawia odświeżanie na `/login`, `/map` itd.

### Zaktualizuj CORS na backendzie

Po pierwszym deployu Pages znasz URL, np. `https://eventradar-abc.pages.dev`:

```bash
# na VPS w /opt/eventradar/.env
CORS_ORIGINS=https://eventradar-abc.pages.dev
docker compose -f docker-compose.hetzner.yml up -d api
```

Przy własnej domenie na Pages dodaj ją po przecinku.

---

## 6. Weryfikacja końcowa

| Test | Oczekiwany wynik |
|------|------------------|
| `https://api.../health` | `{"status":"ok","service":"api"}` |
| `https://app.../` | UI EventRadar |
| Rejestracja / login | działa, token w sessionStorage |
| `https://api.../docs` | Basic auth (login + `DOCS_PASSWORD`) |
| Port 5432 z internetu | **zamknięty** (nmap / skan) |

---

## 7. Aktualizacje

**Backend:**

```bash
cd /opt/eventradar
git pull
docker compose -f docker-compose.hetzner.yml up -d --build
```

**Frontend:** push do gałęzi podpiętej pod Pages → automatyczny rebuild.

---

## 8. Backup Postgres (opcjonalnie, projekt)

```bash
docker compose -f docker-compose.hetzner.yml exec -T postgres \
  pg_dump -U eventradar eventradar > backup-$(date +%F).sql
```

Przychowuj poza VPS (Hetzner Storage Box, lokalnie).

---

## 9. Typowe problemy

| Problem | Rozwiązanie |
|---------|-------------|
| CORS error w przeglądarce | `CORS_ORIGINS` musi **dokładnie** pasować do origin Pages (https, bez `/`) |
| 502 z Caddy | `docker compose ... ps` — czy `api` healthy? `curl localhost:8000/health` |
| `Production configuration invalid` | Sprawdź długość sekretów, `TRUSTED_HOSTS` ≠ `*` |
| `Invalid host header` na `curl 127.0.0.1:8000` | Po `git pull` + rebuild OK; tymczasowo: `curl -H "Host: api.twoja-domena.pl" http://127.0.0.1:8000/health` |
| Brak wydarzeń | `TICKETMASTER_API_KEY` w `.env`, restart `events-service` |
| Pages build fail | Zainstaluj Bun w buildzie lub przełącz na `npm run build` |

---

## Powiązane pliki

- `docker-compose.hetzner.yml` — Postgres + backend (API tylko localhost)
- `deploy/hetzner/Caddyfile` — reverse proxy + TLS
- `docs/DEPLOYMENT.md` — model bezpieczeństwa i zmienne środowiskowe
- `frontend/.env.example` — `VITE_API_URL` dla produkcji
