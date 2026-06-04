import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from user_app.api.deps import get_current_user, get_user_repository
from user_app.db.models import SavedEventListType, User
from user_app.db.session import get_db
from user_app.repositories.custom_event_repository import CustomEventRepository
from user_app.repositories.user_repository import UserAlreadyExistsError, UserRepository
from user_app.schemas.custom_events import CustomEventCreateRequest, CustomEventResponse
from user_app.schemas.users import (
    LoginRequest,
    RegisterRequest,
    SaveAggregatedEventRequest,
    SavedEventResponse,
    TokenResponse,
    UpdateProfileRequest,
    UserPreferences,
    UserProfileResponse,
)
from user_app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/internal/v1")


def _profile_response(user: User) -> UserProfileResponse:
    prefs = user.preferences or {}
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        bio=user.bio,
        location=user.location,
        avatar_url=user.avatar_url,
        preferences=UserPreferences.model_validate(
            {**UserPreferences().model_dump(), **prefs},
        ),
    )


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> TokenResponse:
    from user_app.repositories.user_repository import preferences_to_dict

    if repo.get_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    if repo.get_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    try:
        user = repo.create_user(
            email=body.email,
            password_hash=hash_password(body.password),
            username=body.username,
            full_name=body.full_name,
            bio=body.bio,
            location=body.location,
            avatar_url=body.avatar_url,
            preferences=preferences_to_dict(body.preferences),
        )
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        ) from None
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> TokenResponse:
    user = repo.get_by_email(body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/users/me", response_model=UserProfileResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserProfileResponse:
    return _profile_response(current_user)


@router.patch("/users/me", response_model=UserProfileResponse)
def update_me(
    body: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserProfileResponse:
    prefs = (
        body.preferences.model_dump()
        if body.preferences is not None
        else None
    )
    updated = repo.update_user(
        current_user,
        full_name=body.full_name,
        bio=body.bio,
        location=body.location,
        avatar_url=body.avatar_url,
        preferences=prefs,
    )
    return _profile_response(updated)


@router.get("/users/me/favorites", response_model=list[SavedEventResponse])
def list_favorites(
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> list[SavedEventResponse]:
    rows = repo.list_saved_events(current_user.id, SavedEventListType.FAVORITE)
    return [SavedEventResponse.model_validate(row) for row in rows]


@router.post(
    "/users/me/favorites",
    response_model=SavedEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_favorite(
    body: SaveAggregatedEventRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> SavedEventResponse:
    row = repo.add_saved_aggregated_event(
        user_id=current_user.id,
        list_type=SavedEventListType.FAVORITE,
        public_event_id=body.public_event_id,
        provider=body.provider,
        external_id=body.external_id,
        event_snapshot=body.event_snapshot,
        attended_at=None,
    )
    return SavedEventResponse.model_validate(row)


@router.delete("/users/me/favorites/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    saved_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    if not repo.remove_saved_event(current_user.id, saved_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/users/me/past-events", response_model=list[SavedEventResponse])
def list_past_events(
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> list[SavedEventResponse]:
    rows = repo.list_saved_events(current_user.id, SavedEventListType.PAST)
    return [SavedEventResponse.model_validate(row) for row in rows]


@router.post(
    "/users/me/past-events",
    response_model=SavedEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_past_event(
    body: SaveAggregatedEventRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> SavedEventResponse:
    row = repo.add_saved_aggregated_event(
        user_id=current_user.id,
        list_type=SavedEventListType.PAST,
        public_event_id=body.public_event_id,
        provider=body.provider,
        external_id=body.external_id,
        event_snapshot=body.event_snapshot,
        attended_at=body.attended_at,
    )
    return SavedEventResponse.model_validate(row)


@router.post(
    "/custom-events",
    response_model=CustomEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_custom_event(
    body: CustomEventCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CustomEventResponse:
    repo = CustomEventRepository(db)
    event = repo.create(
        owner_user_id=current_user.id,
        title=body.title,
        short_title=body.short_title,
        description=body.description,
        venue=body.venue,
        location=body.location,
        lat=body.lat,
        lng=body.lng,
        category=body.category,
        category_color=body.category_color,
        price_label=body.price_label,
        image_url=body.image_url,
        tags=body.tags,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        lineup=body.lineup,
        tickets=body.tickets,
        publish=body.publish,
    )
    return CustomEventResponse.model_validate(event)


@router.get("/custom-events/mine", response_model=list[CustomEventResponse])
def list_my_custom_events(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CustomEventResponse]:
    repo = CustomEventRepository(db)
    events = repo.list_for_owner(current_user.id)
    return [CustomEventResponse.model_validate(event) for event in events]


@router.get("/custom-events/published", response_model=list[CustomEventResponse])
def list_published_custom_events(db: Annotated[Session, Depends(get_db)]) -> list[CustomEventResponse]:
    """Public/internal endpoint returning published custom events for aggregation."""
    repo = CustomEventRepository(db)
    events = repo.list_published()
    return [CustomEventResponse.model_validate(event) for event in events]


@router.get("/custom-events/{event_id}", response_model=CustomEventResponse)
def get_custom_event(event_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> CustomEventResponse:
    repo = CustomEventRepository(db)
    event = repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return CustomEventResponse.model_validate(event)
