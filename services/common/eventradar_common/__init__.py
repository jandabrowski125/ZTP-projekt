"""Shared security utilities for EventRadar microservices."""

from eventradar_common.docs_auth import DocsAuthMiddleware
from eventradar_common.internal_auth import InternalServiceAuthMiddleware
from eventradar_common.production import validate_production_settings
from eventradar_common.rate_limit import RateLimitMiddleware
from eventradar_common.security_headers import SecurityHeadersMiddleware

__all__ = [
    "DocsAuthMiddleware",
    "InternalServiceAuthMiddleware",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "validate_production_settings",
]
