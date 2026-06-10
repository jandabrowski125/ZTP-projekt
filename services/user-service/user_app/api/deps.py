from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from user_app.db.models import User
from user_app.db.session import get_db
from user_app.api.auth_helpers import resolve_user_from_bearer_token
from user_app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(
    db: Annotated[Session, Depends(get_db)],
) -> UserRepository:
    return UserRepository(db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = resolve_user_from_bearer_token(credentials.credentials, repo)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user
