from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from httpx import HTTPStatusError
from pydantic import BaseModel, EmailStr, Field

from gateway.clients.user_client import UserServiceClient
from gateway.config import settings
from gateway.dto.users import SavedEventDTO, SaveEventBody, TokenResponseDTO, UpdateProfileBody, UserProfileDTO
from gateway.dto.events import CustomEventCreateBody, CustomEventResponseDTO, CustomEventUpdateBody
from gateway.mappers.user_mapper import to_saved_event_dto, to_user_profile_dto, update_body_to_snake
from gateway.mappers.event_mapper import to_custom_event_dto

router = APIRouter(prefix="/api/v1")


def get_user_client() -> UserServiceClient:
    return UserServiceClient(
        settings.user_service_url,
        internal_token=settings.internal_service_token,
    )


class RegisterBody(BaseModel):
    model_config = {"populate_by_name": True}

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=1, max_length=200, alias="fullName")
    bio: str | None = None
    location: str | None = None
    avatar_url: str | None = Field(default=None, alias="avatarUrl")


class LoginBody(BaseModel):
    email: EmailStr
    password: str


def _proxy_error(exc: HTTPStatusError) -> HTTPException:
    detail = "User service error"
    try:
        body = exc.response.json()
        if isinstance(body, dict) and "detail" in body:
            detail = body["detail"]
    except Exception:
        pass
    return HTTPException(status_code=exc.response.status_code, detail=detail)


def _token_dto(raw: dict) -> TokenResponseDTO:
    return TokenResponseDTO(
        accessToken=raw["access_token"],
        tokenType=raw.get("token_type", "bearer"),
    )


@router.post("/auth/register", response_model=TokenResponseDTO, response_model_by_alias=True)
async def register(
    body: RegisterBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
) -> TokenResponseDTO:
    payload = body.model_dump(by_alias=True, exclude_none=True)
    snake = {
        "email": payload["email"],
        "password": payload["password"],
        "username": payload["username"],
        "full_name": payload["fullName"],
        "bio": payload.get("bio"),
        "location": payload.get("location"),
        "avatar_url": payload.get("avatarUrl"),
    }
    try:
        return _token_dto(await client.register(snake))
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.post("/auth/login", response_model=TokenResponseDTO, response_model_by_alias=True)
async def login(
    body: LoginBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
) -> TokenResponseDTO:
    try:
        return _token_dto(await client.login(body.model_dump(mode="json")))
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/users/me", response_model=UserProfileDTO, response_model_by_alias=True)
async def get_me(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> UserProfileDTO:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        raw = await client.get_me(authorization)
        return to_user_profile_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.patch("/users/me", response_model=UserProfileDTO, response_model_by_alias=True)
async def update_me(
    body: UpdateProfileBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> UserProfileDTO:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = update_body_to_snake(body.model_dump(by_alias=True, exclude_unset=True))
    try:
        raw = await client.update_me(authorization, payload)
        return to_user_profile_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/users/me/favorites", response_model=list[SavedEventDTO], response_model_by_alias=True)
async def list_favorites(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> list[SavedEventDTO]:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        raw_list = await client.list_favorites(authorization)
        return [to_saved_event_dto(item) for item in raw_list]
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.post(
    "/users/me/favorites",
    response_model=SavedEventDTO,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite(
    body: SaveEventBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> SavedEventDTO:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = {
        "public_event_id": body.public_event_id,
        "provider": body.provider,
        "external_id": body.external_id,
        "event_snapshot": body.event_snapshot,
    }
    try:
        raw = await client.add_favorite(authorization, payload)
        return to_saved_event_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.delete("/users/me/favorites/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    saved_id: UUID,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        await client.remove_favorite(authorization, str(saved_id))
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/users/me/past-events", response_model=list[SavedEventDTO], response_model_by_alias=True)
async def list_past_events(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> list[SavedEventDTO]:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        raw_list = await client.list_past_events(authorization)
        return [to_saved_event_dto(item) for item in raw_list]
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.post(
    "/users/me/past-events",
    response_model=SavedEventDTO,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def add_past_event(
    body: SaveEventBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> SavedEventDTO:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = {
        "public_event_id": body.public_event_id,
        "provider": body.provider,
        "external_id": body.external_id,
        "event_snapshot": body.event_snapshot,
        "attended_at": body.attended_at.isoformat() if body.attended_at else None,
    }
    try:
        raw = await client.add_past_event(authorization, payload)
        return to_saved_event_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


# ---------------------------------------------------------------------------
# Custom events (user-created)
# ---------------------------------------------------------------------------


@router.post(
    "/custom-events",
    response_model=CustomEventResponseDTO,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_event(
    body: CustomEventCreateBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> CustomEventResponseDTO:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    # convert camelCase body to snake_case payload for user-service
    payload = {
        "title": body.title,
        "short_title": body.short_title,
        "description": body.description,
        "venue": body.venue,
        "location": body.location,
        "lat": body.lat,
        "lng": body.lng,
        "category": body.category,
        "category_color": body.category_color,
        "price_label": body.price_label,
        "image_url": body.image_url,
        "tags": body.tags,
        "starts_at": body.starts_at.isoformat(),
        "ends_at": body.ends_at.isoformat() if body.ends_at else None,
        "lineup": body.lineup,
        "tickets": body.tickets,
        "publish": body.publish,
    }
    try:
        raw = await client.create_custom_event(authorization, payload)
        return to_custom_event_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/custom-events", response_model=list[CustomEventResponseDTO], response_model_by_alias=True)
async def list_published_custom_events(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
) -> list[CustomEventResponseDTO]:
    try:
        raw_list = await client.list_published_custom_events()
        return [to_custom_event_dto(item) for item in raw_list]
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/custom-events/mine", response_model=list[CustomEventResponseDTO], response_model_by_alias=True)
async def list_my_custom_events(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> list[CustomEventResponseDTO]:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        raw_list = await client.list_my_custom_events(authorization)
        return [to_custom_event_dto(item) for item in raw_list]
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.patch(
    "/custom-events/{event_id}",
    response_model=CustomEventResponseDTO,
    response_model_by_alias=True,
)
async def update_custom_event(
    event_id: UUID,
    body: CustomEventUpdateBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> CustomEventResponseDTO:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = body.model_dump(exclude_unset=True)
    if "starts_at" in payload and payload["starts_at"] is not None:
        payload["starts_at"] = payload["starts_at"].isoformat()
    if "ends_at" in payload and payload["ends_at"] is not None:
        payload["ends_at"] = payload["ends_at"].isoformat()
    try:
        raw = await client.update_custom_event(authorization, str(event_id), payload)
        return to_custom_event_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.delete("/custom-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_event(
    event_id: UUID,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        await client.delete_custom_event(authorization, str(event_id))
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc
