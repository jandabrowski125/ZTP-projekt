"""Fail fast when production secrets or CORS are misconfigured."""

from __future__ import annotations

WEAK_JWT_SECRETS = frozenset(
    {
        "",
        "change-me-in-production",
        "dev-change-me",
        "changeme",
        "secret",
    }
)


def validate_production_settings(
    *,
    app_env: str,
    jwt_secret: str | None = None,
    internal_service_token: str | None = None,
    cors_origins: str | None = None,
    docs_password: str | None = None,
    database_url: str | None = None,
    trusted_hosts: str | None = None,
) -> None:
    if app_env != "production":
        return

    errors: list[str] = []

    if jwt_secret is not None and (
        jwt_secret in WEAK_JWT_SECRETS or len(jwt_secret) < 32
    ):
        errors.append("JWT_SECRET must be at least 32 characters and not a default value")

    if internal_service_token is not None and (
        not internal_service_token or len(internal_service_token) < 32
    ):
        errors.append("INTERNAL_SERVICE_TOKEN must be at least 32 characters")

    if cors_origins is not None:
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
        if not origins or "*" in origins:
            errors.append("CORS_ORIGINS must list explicit frontend origins (no wildcard)")

    if docs_password is not None:
        if not docs_password:
            errors.append("DOCS_PASSWORD is required in production (Swagger / admin docs)")
        elif len(docs_password) < 16:
            errors.append("DOCS_PASSWORD must be at least 16 characters in production")

    if database_url is not None and (
        "eventradar:eventradar@" in database_url and "localhost" not in database_url
    ):
        errors.append("DATABASE_URL must not use default dev credentials in production")

    if trusted_hosts is not None:
        hosts = [host.strip() for host in trusted_hosts.split(",") if host.strip()]
        if not hosts or trusted_hosts.strip() == "*":
            errors.append("TRUSTED_HOSTS must list explicit API hostnames in production")

    if errors:
        msg = "Production configuration invalid:\n- " + "\n- ".join(errors)
        raise RuntimeError(msg)
