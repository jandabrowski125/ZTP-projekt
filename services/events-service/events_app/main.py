from fastapi import FastAPI

from eventradar_common.docs_auth import DocsAuthMiddleware
from eventradar_common.internal_auth import InternalServiceAuthMiddleware
from eventradar_common.production import validate_production_settings
from eventradar_common.security_headers import SecurityHeadersMiddleware
from events_app.api.routes import router
from events_app.config import settings
from events_app.providers.factory import build_event_repository
from events_app.services.event_service import EventService

validate_production_settings(
    app_env=settings.app_env,
    internal_service_token=settings.internal_service_token,
    docs_password=settings.docs_password,
)

event_service: EventService | None = None


def init_event_service() -> EventService:
    global event_service
    if event_service is None:
        event_service = EventService(build_event_repository(settings))
    return event_service


app = FastAPI(
    title="EventRadar Events Service",
    description="Internal service exposing normalized event data from external providers",
    version="0.2.0",
    docs_url="/docs",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    DocsAuthMiddleware,
    username=settings.docs_username,
    password=settings.docs_password,
    app_env=settings.app_env,
)
app.add_middleware(
    InternalServiceAuthMiddleware,
    internal_token=settings.internal_service_token,
    app_env=settings.app_env,
)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    provider = "ticketmaster" if settings.ticketmaster_api_key.strip() else "none"
    return {"status": "ok", "service": "events-service", "provider": provider}
