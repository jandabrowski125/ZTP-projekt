from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from eventradar_common.docs_auth import DocsAuthMiddleware
from eventradar_common.production import validate_production_settings
from eventradar_common.rate_limit import RateLimitMiddleware
from eventradar_common.security_headers import SecurityHeadersMiddleware
from gateway.api.routes import router
from gateway.api.user_routes import router as user_router
from gateway.clients.events_client import EventsServiceClient
from gateway.config import settings
from gateway.services.event_facade import EventFacade

validate_production_settings(
    app_env=settings.app_env,
    internal_service_token=settings.internal_service_token,
    cors_origins=settings.cors_origins,
    docs_password=settings.docs_password,
    trusted_hosts=settings.trusted_hosts,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


event_facade = EventFacade(
    EventsServiceClient(
        settings.events_service_url,
        internal_token=settings.internal_service_token,
    )
)

app = FastAPI(
    title="EventRadar API",
    description="Public REST API for the EventRadar frontend",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if settings.is_production and not _origins:
    raise RuntimeError("CORS_ORIGINS must be set in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    rules={
        "/api/v1/auth/register": (5, 60),
        "/api/v1/auth/login": (10, 60),
        "/docs": (20, 60),
        "/openapi.json": (20, 60),
    },
    default_rule=(120, 60),
    trust_proxy_headers=settings.trust_proxy_headers,
)
app.add_middleware(
    DocsAuthMiddleware,
    username=settings.docs_username,
    password=settings.docs_password,
    app_env=settings.app_env,
)

if settings.is_production and settings.trusted_hosts != "*":
    hosts = [host.strip() for host in settings.trusted_hosts.split(",") if host.strip()]
    # Allow local healthchecks (Docker, curl on VPS) and Caddy → 127.0.0.1 upstream.
    for internal in ("localhost", "127.0.0.1"):
        if internal not in hosts:
            hosts.append(internal)
    if hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

app.include_router(router)
app.include_router(user_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}
