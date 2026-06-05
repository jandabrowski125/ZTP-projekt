"""Simple in-memory rate limiting for public API endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter keyed by client IP and path prefix."""

    def __init__(
        self,
        app,
        *,
        rules: dict[str, tuple[int, int]],
        default_rule: tuple[int, int] | None = None,
        key_func: Callable[[Request], str] | None = None,
        trust_proxy_headers: bool = False,
    ) -> None:
        super().__init__(app)
        self._rules = rules
        self._default_rule = default_rule
        self._trust_proxy = trust_proxy_headers
        self._key_func = key_func or (lambda req: _client_ip(req, self._trust_proxy))
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        rule = self._match_rule(request.url.path)
        if rule is None:
            return await call_next(request)

        max_requests, window_seconds = rule
        now = time.monotonic()
        bucket_key = f"{self._key_func(request)}:{request.url.path.split('?')[0]}"
        hits = self._hits[bucket_key]

        while hits and now - hits[0] > window_seconds:
            hits.popleft()

        if len(hits) >= max_requests:
            retry_after = max(1, int(window_seconds - (now - hits[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        return await call_next(request)

    def _match_rule(self, path: str) -> tuple[int, int] | None:
        for prefix, rule in self._rules.items():
            if path.startswith(prefix):
                return rule
        return self._default_rule


def _client_ip(request: Request, trust_proxy_headers: bool = False) -> str:
    if trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
