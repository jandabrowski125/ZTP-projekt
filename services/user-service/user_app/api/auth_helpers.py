"""Resolve authenticated users from internal JWTs or Firebase ID tokens."""

from __future__ import annotations

import uuid

from user_app.firebase_auth import (
    FirebaseAuthError,
    firebase_email_from_claims,
    firebase_uid_from_claims,
    is_firebase_configured,
    verify_firebase_id_token,
)
from user_app.repositories.user_repository import UserRepository
from user_app.security import decode_access_token


def resolve_user_from_bearer_token(token: str, repo: UserRepository):
    user = _user_from_internal_jwt(token, repo)
    if user is not None:
        return user
    if not is_firebase_configured():
        return None
    return _user_from_firebase_token(token, repo)


def _user_from_internal_jwt(token: str, repo: UserRepository):
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    try:
        parsed_id = uuid.UUID(user_id)
    except ValueError:
        return None
    user = repo.get_by_id(parsed_id)
    if user is None or not user.is_active:
        return None
    return user


def _user_from_firebase_token(token: str, repo: UserRepository):
    try:
        claims = verify_firebase_id_token(token)
    except FirebaseAuthError:
        return None

    firebase_uid = firebase_uid_from_claims(claims)
    if firebase_uid:
        try:
            user = repo.get_by_firebase_uid(firebase_uid)
            if user is not None and user.is_active:
                return user
        except Exception:
            # Column may not exist yet if migration 003 hasn't run.
            pass

    email = firebase_email_from_claims(claims)
    if email:
        try:
            user = repo.get_by_email(email)
            if user is not None and user.is_active:
                if firebase_uid and user.firebase_uid is None:
                    try:
                        return repo.link_firebase_uid(user, firebase_uid)
                    except Exception:
                        return user
                return user
        except Exception:
            pass

    return None


def optional_firebase_claims(token: str | None) -> dict | None:
    if not token or not is_firebase_configured():
        return None
    try:
        return verify_firebase_id_token(token)
    except FirebaseAuthError:
        return None
