import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventradar_common.docs_auth import DocsAuthMiddleware
from eventradar_common.internal_auth import INTERNAL_HEADER, InternalServiceAuthMiddleware
from eventradar_common.production import validate_production_settings
from eventradar_common.rate_limit import RateLimitMiddleware


@pytest.fixture
def internal_app() -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/internal/v1/events")
    def internal_events() -> dict[str, str]:
        return {"events": "ok"}

    app.add_middleware(
        InternalServiceAuthMiddleware,
        internal_token="test-internal-token-32-chars-minimum!!",
        app_env="production",
    )
    return app


def test_internal_auth_blocks_missing_token(internal_app: FastAPI) -> None:
    client = TestClient(internal_app)
    assert client.get("/health").status_code == 200
    assert client.get("/internal/v1/events").status_code == 403


def test_internal_auth_allows_valid_token(internal_app: FastAPI) -> None:
    client = TestClient(internal_app)
    response = client.get(
        "/internal/v1/events",
        headers={INTERNAL_HEADER: "test-internal-token-32-chars-minimum!!"},
    )
    assert response.status_code == 200


def test_docs_auth_requires_password() -> None:
    app = FastAPI(docs_url="/docs", openapi_url="/openapi.json")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(
        DocsAuthMiddleware,
        username="admin",
        password="secret-docs-pass",
        app_env="production",
    )
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/openapi.json").status_code == 401

    token = base64.b64encode(b"admin:secret-docs-pass").decode()
    auth = client.get("/openapi.json", headers={"Authorization": f"Basic {token}"})
    assert auth.status_code == 200


def test_rate_limit_returns_429() -> None:
    app = FastAPI()

    @app.post("/api/v1/auth/login")
    def login() -> dict[str, str]:
        return {"ok": "true"}

    app.add_middleware(
        RateLimitMiddleware,
        rules={"/api/v1/auth/login": (2, 60)},
    )
    client = TestClient(app)
    assert client.post("/api/v1/auth/login").status_code == 200
    assert client.post("/api/v1/auth/login").status_code == 200
    assert client.post("/api/v1/auth/login").status_code == 429


def test_internal_auth_headers_helper() -> None:
    from eventradar_common.internal_auth import internal_auth_headers

    token = "test-internal-token-32-chars-minimum!!"
    assert internal_auth_headers(token) == {INTERNAL_HEADER: token}
    assert internal_auth_headers("") == {}


def test_production_validation_rejects_weak_secrets() -> None:
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_settings(
            app_env="production",
            jwt_secret="change-me-in-production",
            internal_service_token="x" * 32,
            cors_origins="https://app.example.com",
            docs_password="strong-docs-password",
            trusted_hosts="api.example.com",
        )


def test_production_validation_rejects_wildcard_trusted_hosts() -> None:
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        validate_production_settings(
            app_env="production",
            jwt_secret="x" * 32,
            internal_service_token="y" * 32,
            cors_origins="https://app.example.com",
            docs_password="strong-docs-password",
            trusted_hosts="*",
        )
