"""Sanitize upstream HTTP errors before returning them to API clients."""

from __future__ import annotations

from fastapi import HTTPException
from httpx import HTTPStatusError


def upstream_http_error(
    exc: HTTPStatusError,
    *,
    not_found_detail: str | None = None,
) -> HTTPException:
    status = exc.response.status_code
    if status == 404 and not_found_detail:
        return HTTPException(status_code=404, detail=not_found_detail)

    detail: str = "Upstream service error"
    if status < 500:
        try:
            body = exc.response.json()
            if isinstance(body, dict):
                raw = body.get("detail")
                if isinstance(raw, str) and raw:
                    detail = raw
        except Exception:
            pass

    client_status = 502 if status >= 500 else status
    return HTTPException(status_code=client_status, detail=detail)
