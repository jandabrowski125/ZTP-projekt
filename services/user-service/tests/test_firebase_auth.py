from unittest.mock import patch

from user_app.api.auth_helpers import optional_firebase_claims, resolve_user_from_bearer_token
from user_app.repositories.user_repository import UserRepository
from user_app.security import hash_password


def test_register_with_firebase_token_links_account(api_client):
    claims = {
        "uid": "firebase-user-123",
        "email": "firebase@example.com",
    }
    with patch("user_app.api.routes.optional_firebase_claims", return_value=claims):
        response = api_client.post(
            "/internal/v1/auth/register",
            json={
                "email": "firebase@example.com",
                "username": "firebaseuser",
                "full_name": "Firebase User",
            },
            headers={"Authorization": "Bearer firebase-id-token"},
        )
    assert response.status_code == 201

    with patch(
        "user_app.api.auth_helpers.verify_firebase_id_token",
        return_value=claims,
    ):
        me = api_client.get(
            "/internal/v1/users/me",
            headers={"Authorization": "Bearer firebase-id-token"},
        )
    assert me.status_code == 200
    assert me.json()["email"] == "firebase@example.com"
    assert me.json()["username"] == "firebaseuser"


def test_firebase_token_email_mismatch_rejected(api_client):
    claims = {
        "uid": "firebase-user-456",
        "email": "real@example.com",
    }
    with patch("user_app.api.routes.optional_firebase_claims", return_value=claims):
        response = api_client.post(
            "/internal/v1/auth/register",
            json={
                "email": "other@example.com",
                "username": "otheruser",
                "full_name": "Other User",
            },
            headers={"Authorization": "Bearer firebase-id-token"},
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email does not match Firebase account"


def test_resolve_user_links_existing_email_to_firebase_uid(db_session):
    repo = UserRepository(db_session)
    user = repo.create_user(
        email="legacy@example.com",
        password_hash=hash_password("Secure1!"),
        username="legacyuser",
        full_name="Legacy User",
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )
    claims = {"uid": "firebase-legacy-uid", "email": "legacy@example.com"}

    with patch("user_app.api.auth_helpers.verify_firebase_id_token", return_value=claims):
        resolved = resolve_user_from_bearer_token("firebase-token", repo)

    assert resolved is not None
    assert resolved.id == user.id
    assert resolved.firebase_uid == "firebase-legacy-uid"


def test_optional_firebase_claims_returns_none_when_not_configured():
    with patch("user_app.api.auth_helpers.is_firebase_configured", return_value=False):
        assert optional_firebase_claims("any-token") is None


def test_internal_jwt_still_works_after_firebase_support(api_client):
    register = api_client.post(
        "/internal/v1/auth/register",
        json={
            "email": "jwt@example.com",
            "password": "Secure1!",
            "username": "jwtuser",
            "full_name": "JWT User",
        },
    )
    assert register.status_code == 201
    token = register.json()["access_token"]

    me = api_client.get(
        "/internal/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "jwtuser"
