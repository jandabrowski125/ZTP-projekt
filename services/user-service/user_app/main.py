from fastapi import FastAPI, Response, status

from eventradar_common.docs_auth import DocsAuthMiddleware
from eventradar_common.internal_auth import InternalServiceAuthMiddleware
from eventradar_common.production import validate_production_settings
from eventradar_common.security_headers import SecurityHeadersMiddleware
from user_app.api.routes import router
from user_app.api.user_engagement_routes import router as engagement_router
from user_app.config import settings
from user_app.db.bootstrap import verify_schema

validate_production_settings(
    app_env=settings.app_env,
    jwt_secret=settings.jwt_secret,
    internal_service_token=settings.internal_service_token,
    docs_password=settings.docs_password,
    database_url=settings.database_url,
)

app = FastAPI(
    title="EventRadar User Service",
    description="Users, favorites, past events, and custom venue events",
    version="0.1.0",
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
app.include_router(engagement_router)


@app.get("/health")
def health(response: Response) -> dict[str, str]:
    try:
        verify_schema()
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "service": "user-service",
            "database": "unavailable",
        }
    return {"status": "ok", "service": "user-service", "database": "ready"}
