from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway.api.routes import router
from gateway.api.user_routes import router as user_router
from gateway.clients.events_client import EventsServiceClient
from gateway.config import settings
from gateway.services.event_facade import EventFacade

event_facade = EventFacade(EventsServiceClient(settings.events_service_url))

app = FastAPI(
    title="EventRadar API",
    description="Public REST API for the EventRadar frontend",
    version="0.1.0",
    docs_url="/docs",
)

_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(user_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}
