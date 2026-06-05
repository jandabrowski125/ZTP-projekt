"""Require a shared secret for service-to-service calls on internal routes."""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

INTERNAL_HEADER = "X-Internal-Service-Token"
PUBLIC_PATHS = frozenset({"/health"})


class InternalServiceAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        internal_token: str,
        app_env: str = "development",
        protect_prefix: str = "/internal/",
    ) -> None:
        super().__init__(app)
        self._token = internal_token
        self._app_env = app_env
        self._protect_prefix = protect_prefix

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in PUBLIC_PATHS or not path.startswith(self._protect_prefix):
            return await call_next(request)

        if not self._token:
            if self._app_env == "production":
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Internal service authentication is not configured"},
                )
            return await call_next(request)

        provided = request.headers.get(INTERNAL_HEADER, "")
        if not secrets.compare_digest(provided, self._token):
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        return await call_next(request)


def internal_auth_headers(internal_token: str) -> dict[str, str]:
    if not internal_token:
        return {}
    return {INTERNAL_HEADER: internal_token}
