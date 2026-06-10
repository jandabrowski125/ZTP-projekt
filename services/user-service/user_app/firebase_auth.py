"""Verify Firebase ID tokens issued to the EventRadar frontend."""

from __future__ import annotations

import logging

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from user_app.config import settings

logger = logging.getLogger(__name__)


class FirebaseAuthError(Exception):
    """Raised when a Firebase ID token cannot be verified."""


def is_firebase_configured() -> bool:
    return bool(settings.firebase_project_id.strip())


def verify_firebase_id_token(token: str) -> dict:
    project_id = settings.firebase_project_id.strip()
    if not project_id:
        raise FirebaseAuthError("Firebase is not configured")

    try:
        return id_token.verify_firebase_token(
            token,
            google_requests.Request(),
            audience=project_id,
        )
    except ValueError as exc:
        logger.debug("Firebase token verification failed: %s", exc)
        raise FirebaseAuthError(str(exc)) from exc


def firebase_uid_from_claims(claims: dict) -> str | None:
    uid = claims.get("uid") or claims.get("user_id") or claims.get("sub")
    return str(uid) if uid else None


def firebase_email_from_claims(claims: dict) -> str | None:
    email = claims.get("email")
    return str(email).lower() if email else None
