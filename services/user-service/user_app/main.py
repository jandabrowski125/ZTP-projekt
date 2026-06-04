from fastapi import FastAPI, Response, status

from user_app.api.routes import router
from user_app.db.bootstrap import verify_schema

app = FastAPI(
    title="EventRadar User Service",
    description="Users, favorites, past events, and custom venue events",
    version="0.1.0",
)

app.include_router(router)


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
