"""HTTP Basic authentication for Swagger / OpenAPI admin panels."""

from __future__ import annotations

import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

DOCS_PATH_PREFIXES = ("/docs", "/redoc", "/openapi.json")


def _is_docs_path(path: str) -> bool:
    return path == "/openapi.json" or any(
        path == prefix or path.startswith(f"{prefix}/") for prefix in DOCS_PATH_PREFIXES
    )


def _check_basic(auth_header: str | None, username: str, password: str) -> bool:
    if not auth_header or not auth_header.lower().startswith("basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    user, _, pwd = decoded.partition(":")
    return secrets.compare_digest(user, username) and secrets.compare_digest(pwd, password)


class DocsAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        username: str,
        password: str,
        app_env: str = "development",
    ) -> None:
        super().__init__(app)
        self._username = username
        self._password = password
        self._app_env = app_env

    async def dispatch(self, request: Request, call_next) -> Response:
        if not _is_docs_path(request.url.path):
            return await call_next(request)

        if not self._password:
            if self._app_env == "production":
                return Response(status_code=404)
            return await call_next(request)

        if not _check_basic(request.headers.get("Authorization"), self._username, self._password):
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="EventRadar API Docs"'},
                content="Authentication required",
                media_type="text/plain",
            )

        return await call_next(request)
