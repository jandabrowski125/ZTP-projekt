import re as _re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fastapi.security import HTTPAuthorizationCredentials

from user_app.api.auth_helpers import optional_firebase_claims
from user_app.api.deps import bearer_scheme, get_current_user, get_user_repository
from user_app.firebase_auth import (
    FirebaseAuthError,
    firebase_email_from_claims,
    firebase_uid_from_claims,
    is_firebase_configured,
    verify_firebase_id_token,
)
from user_app.db.models import SavedEventListType, User
from user_app.db.session import get_db
from user_app.repositories.custom_event_repository import CustomEventRepository
from user_app.repositories.user_repository import UserAlreadyExistsError, UserRepository
from user_app.schemas.custom_events import (
    CustomEventCreateRequest,
    CustomEventResponse,
    CustomEventUpdateRequest,
)
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
from user_app.security import create_access_token, generate_opaque_token, hash_password, verify_password
from user_app.validation import validate_strong_password

router = APIRouter(prefix="/internal/v1")


def _unique_username(repo: UserRepository, base: str) -> str:
    candidate = _re.sub(r"[^a-zA-Z0-9._-]", "_", base)[:60].strip("_") or "user"
    suffix = 1
    while repo.get_by_username(candidate) is not None:
        candidate = f"{candidate[:55]}_{suffix}"
        suffix += 1
    return candidate


@router.post("/auth/firebase", response_model=TokenResponse)
def firebase_token_exchange(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> TokenResponse:
    """Exchange a Firebase ID token for an internal JWT.

    Called once after Firebase sign-in so that all subsequent API calls
    use a standard short-lived JWT instead of repeating Firebase network
    verification on every request.
    """
    from user_app.repositories.user_repository import preferences_to_dict

    if not is_firebase_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase authentication is not configured on this server",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token required in Authorization header",
        )

    try:
        claims = verify_firebase_id_token(credentials.credentials)
    except FirebaseAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Firebase token invalid: {exc}",
        ) from exc

    firebase_uid = firebase_uid_from_claims(claims)
    email = firebase_email_from_claims(claims)
    if not firebase_uid or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase token is missing uid or email claims",
        )

    # 1) Exact match by firebase_uid
    user = repo.get_by_firebase_uid(firebase_uid)
    if user is not None and user.is_active:
        return TokenResponse(access_token=create_access_token(str(user.id)))

    # 2) Match by email → link firebase_uid to existing account
    user = repo.get_by_email(email)
    if user is not None and user.is_active:
        if user.firebase_uid is None:
            user = repo.link_firebase_uid(user, firebase_uid)
        return TokenResponse(access_token=create_access_token(str(user.id)))

    # 3) Auto-provision a backend user for a Firebase-only account
    display_name = (claims.get("name") or email.split("@")[0]).strip() or email.split("@")[0]
    username = _unique_username(repo, email.split("@")[0])
    photo_url = claims.get("picture") or None
    try:
        user = repo.create_user(
            email=email,
            firebase_uid=firebase_uid,
            password_hash=hash_password(generate_opaque_token()),
            username=username,
            full_name=display_name,
            bio=None,
            location=None,
            avatar_url=photo_url,
            preferences=preferences_to_dict(None),
        )
    except UserAlreadyExistsError:
        existing = repo.get_by_email(email) or repo.get_by_firebase_uid(firebase_uid)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account conflict during auto-provisioning",
            ) from None
        user = existing

    return TokenResponse(access_token=create_access_token(str(user.id)))


def _custom_event_response(event) -> CustomEventResponse:
    return CustomEventResponse(
        id=event.id,
        owner_user_id=event.owner_user_id,
        owner_username=event.owner.username if event.owner else None,
        title=event.title,
        short_title=event.short_title,
        description=event.description,
        venue=event.venue,
        location=event.location,
        address_line=event.address_line,
        postal_code=event.postal_code,
        lat=event.lat,
        lng=event.lng,
        category=event.category,
        category_color=event.category_color,
        price_label=event.price_label,
        image_url=event.image_url,
        tags=event.tags,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        event_timezone=event.event_timezone,
        status=event.status.value if hasattr(event.status, "value") else str(event.status),
        lineup=event.lineup,
        tickets=event.tickets,
    )


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


def _register_with_firebase(
    body: RegisterRequest,
    claims: dict,
    repo: UserRepository,
) -> TokenResponse:
    from user_app.repositories.user_repository import preferences_to_dict

    firebase_uid = firebase_uid_from_claims(claims)
    firebase_email = firebase_email_from_claims(claims)
    if not firebase_uid or not firebase_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token",
        )
    if body.email.lower() != firebase_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email does not match Firebase account",
        )

    existing = repo.get_by_firebase_uid(firebase_uid)
    if existing is not None:
        return TokenResponse(access_token=create_access_token(str(existing.id)))

    by_email = repo.get_by_email(body.email)
    if by_email is not None:
        if by_email.firebase_uid and by_email.firebase_uid != firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        linked = repo.link_firebase_uid(by_email, firebase_uid)
        return TokenResponse(access_token=create_access_token(str(linked.id)))

    if repo.get_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    try:
        user = repo.create_user(
            email=body.email,
            firebase_uid=firebase_uid,
            password_hash=hash_password(generate_opaque_token()),
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
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> TokenResponse:
    from user_app.repositories.user_repository import preferences_to_dict

    firebase_claims = (
        optional_firebase_claims(credentials.credentials)
        if credentials is not None and credentials.scheme.lower() == "bearer"
        else None
    )
    if firebase_claims is not None:
        return _register_with_firebase(body, firebase_claims, repo)

    if not body.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password required",
        )
    try:
        validate_strong_password(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

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
        address_line=body.address_line,
        postal_code=body.postal_code,
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
    return _custom_event_response(event)


@router.get("/custom-events/mine", response_model=list[CustomEventResponse])
def list_my_custom_events(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CustomEventResponse]:
    repo = CustomEventRepository(db)
    events = repo.list_for_owner(current_user.id)
    return [_custom_event_response(event) for event in events]


@router.get("/custom-events/published", response_model=list[CustomEventResponse])
def list_published_custom_events(db: Annotated[Session, Depends(get_db)]) -> list[CustomEventResponse]:
    """Public/internal endpoint returning published custom events for aggregation."""
    repo = CustomEventRepository(db)
    events = repo.list_published()
    return [_custom_event_response(event) for event in events]


@router.get("/custom-events/{event_id}", response_model=CustomEventResponse)
def get_custom_event(event_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> CustomEventResponse:
    repo = CustomEventRepository(db)
    event = repo.get(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _custom_event_response(event)


@router.patch("/custom-events/{event_id}", response_model=CustomEventResponse)
def update_custom_event(
    event_id: uuid.UUID,
    body: CustomEventUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CustomEventResponse:
    repo = CustomEventRepository(db)
    payload = body.model_dump(exclude_unset=True)
    event = repo.update(event_id, owner_user_id=current_user.id, **payload)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _custom_event_response(event)


@router.delete("/custom-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_event(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    repo = CustomEventRepository(db)
    if not repo.delete(event_id, owner_user_id=current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
