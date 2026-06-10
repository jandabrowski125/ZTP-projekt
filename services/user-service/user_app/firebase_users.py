"""Helpers for creating/linking users from Firebase sign-in."""

from __future__ import annotations

import re
import secrets

from user_app.repositories.user_repository import UserRepository
from user_app.schemas.users import UserPreferences
from user_app.security import hash_password


def _sanitize_username(base: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "", base.lower())[:64]
    return cleaned or "user"


def _unique_username(repo: UserRepository, base: str, suffix: str) -> str:
    candidate = _sanitize_username(base)[: max(1, 64 - len(suffix))]
    candidate = f"{candidate}{suffix}"[:64]
    if not repo.get_by_username(candidate):
        return candidate

    for index in range(1, 100):
        alt = f"{candidate[: max(1, 64 - len(str(index)))]}{index}"[:64]
        if not repo.get_by_username(alt):
            return alt

    return _sanitize_username(f"user{suffix}")[:64]


def get_or_create_firebase_user(
    repo: UserRepository,
    *,
    firebase_uid: str,
    email: str,
    full_name: str,
    avatar_url: str | None,
) -> tuple[object, bool]:
    """Return (user, created). Links existing email accounts when possible."""
    existing = repo.get_by_firebase_uid(firebase_uid)
    if existing is not None:
        return existing, False

    by_email = repo.get_by_email(email)
    if by_email is not None:
        if by_email.firebase_uid and by_email.firebase_uid != firebase_uid:
            msg = "Email already linked to a different Firebase account"
            raise ValueError(msg)
        updated = repo.update_user(
            by_email,
            firebase_uid=firebase_uid,
            full_name=full_name or by_email.full_name,
            avatar_url=avatar_url or by_email.avatar_url,
        )
        return updated, False

    username = _unique_username(repo, email.split("@")[0], firebase_uid[:6])
    user = repo.create_firebase_user(
        firebase_uid=firebase_uid,
        email=email,
        username=username,
        full_name=full_name,
        avatar_url=avatar_url,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        preferences=UserPreferences().model_dump(),
    )
    return user, True
