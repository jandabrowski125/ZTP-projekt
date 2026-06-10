from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from httpx import HTTPStatusError
from pydantic import BaseModel, EmailStr, Field

from gateway.clients.events_client import EventsServiceClient
from gateway.clients.user_client import UserServiceClient
from gateway.config import settings
from gateway.dto.events import (
    CustomEventCreateBody,
    CustomEventResponseDTO,
    CustomEventUpdateBody,
    EventDataDTO,
)
from gateway.dto.user_events import (
    EventActionStatusDTO,
    EventRefBody,
    NotificationsResponseDTO,
    ReminderBody,
    SavedEventsListDTO,
)
from gateway.dto.users import SavedEventDTO, SaveEventBody, TokenResponseDTO, UpdateProfileBody, UserProfileDTO
from gateway.mappers.event_mapper import to_custom_event_dto, to_event_data_dto
from gateway.mappers.user_events_mapper import to_event_action_status_dto, to_notification_dto
from gateway.mappers.user_mapper import to_saved_event_dto, to_user_profile_dto, update_body_to_snake
from gateway.services.event_ref_resolver import resolve_event_ref

router = APIRouter(prefix="/api/v1")


def get_user_client() -> UserServiceClient:
    return UserServiceClient(
        settings.user_service_url,
        internal_token=settings.internal_service_token,
    )


def get_events_client() -> EventsServiceClient:
    return EventsServiceClient(
        settings.events_service_url,
        internal_token=settings.internal_service_token,
    )


def _require_auth(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return authorization


async def _saved_rows_to_items(
    rows: list[dict[str, Any]],
    events_client: EventsServiceClient,
) -> list[EventDataDTO]:
    items: list[EventDataDTO] = []
    for row in rows:
        public_id = row.get("public_event_id")
        if public_id is None:
            continue
        try:
            raw = await events_client.get_event(public_id)
            items.append(to_event_data_dto(raw))
        except HTTPStatusError:
            continue
    return items


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


@router.post("/auth/firebase", response_model=TokenResponseDTO, response_model_by_alias=True)
async def firebase_token_exchange(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> TokenResponseDTO:
    """Exchange a Firebase ID token for an internal JWT session token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token required in Authorization header",
        )
    try:
        return _token_dto(await client.exchange_firebase_token(authorization))
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


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


@router.get("/users/me/favorites", response_model=SavedEventsListDTO, response_model_by_alias=True)
async def list_favorites(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    events_client: Annotated[EventsServiceClient, Depends(get_events_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> SavedEventsListDTO:
    auth = _require_auth(authorization)
    try:
        raw_list = await client.list_favorites(auth)
        items = await _saved_rows_to_items(raw_list, events_client)
        return SavedEventsListDTO(items=items)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.put("/users/me/favorites", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_favorite(
    body: EventRefBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    events_client: Annotated[EventsServiceClient, Depends(get_events_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    auth = _require_auth(authorization)
    target = await resolve_event_ref(body, events_client)
    try:
        await client.upsert_favorite(auth, target.to_service_dict())
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.delete("/users/me/favorites", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_by_ref(
    body: EventRefBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    events_client: Annotated[EventsServiceClient, Depends(get_events_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    auth = _require_auth(authorization)
    target = await resolve_event_ref(body, events_client)
    try:
        await client.remove_favorite_by_ref(auth, target.to_service_dict())
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/users/me/event-actions", response_model=EventActionStatusDTO, response_model_by_alias=True)
async def get_event_action_status(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    events_client: Annotated[EventsServiceClient, Depends(get_events_client)],
    authorization: Annotated[str | None, Header()] = None,
    event_id: int = Query(alias="eventId"),
    community_event_id: str | None = Query(default=None, alias="communityEventId"),
) -> EventActionStatusDTO:
    auth = _require_auth(authorization)
    ref = EventRefBody(eventId=event_id, communityEventId=community_event_id)
    target = await resolve_event_ref(ref, events_client)
    try:
        raw = await client.get_event_action_status(auth, target.to_service_dict())
        return to_event_action_status_dto(raw)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/users/me/enrolled", response_model=SavedEventsListDTO, response_model_by_alias=True)
async def list_enrolled(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    events_client: Annotated[EventsServiceClient, Depends(get_events_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> SavedEventsListDTO:
    auth = _require_auth(authorization)
    try:
        raw_list = await client.list_enrolled(auth)
        items = await _saved_rows_to_items(raw_list, events_client)
        return SavedEventsListDTO(items=items)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.put("/users/me/enrolled", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_enrolled(
    body: EventRefBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    events_client: Annotated[EventsServiceClient, Depends(get_events_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    auth = _require_auth(authorization)
    target = await resolve_event_ref(body, events_client)
    try:
        await client.upsert_enrolled(auth, target.to_service_dict())
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.delete("/users/me/enrolled", status_code=status.HTTP_204_NO_CONTENT)
async def remove_enrolled_by_ref(
    body: EventRefBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    events_client: Annotated[EventsServiceClient, Depends(get_events_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    auth = _require_auth(authorization)
    target = await resolve_event_ref(body, events_client)
    try:
        await client.remove_enrolled_by_ref(auth, target.to_service_dict())
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.put("/users/me/reminders", status_code=status.HTTP_204_NO_CONTENT)
async def set_event_reminder(
    body: ReminderBody,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    events_client: Annotated[EventsServiceClient, Depends(get_events_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    auth = _require_auth(authorization)
    ref = EventRefBody(eventId=body.event_id, communityEventId=body.community_event_id)
    target = await resolve_event_ref(ref, events_client)
    payload = target.to_service_dict()
    payload["enabled"] = body.enabled
    if body.starts_at is not None:
        payload["starts_at"] = body.starts_at.isoformat()
    try:
        await client.set_event_reminder(auth, payload)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.get("/users/me/notifications", response_model=NotificationsResponseDTO, response_model_by_alias=True)
async def list_notifications(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> NotificationsResponseDTO:
    auth = _require_auth(authorization)
    try:
        raw = await client.list_notifications(auth)
        return NotificationsResponseDTO(
            items=[to_notification_dto(item) for item in raw.get("items", [])],
            unreadCount=int(raw.get("unread_count", 0)),
        )
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.patch("/users/me/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: UUID,
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    auth = _require_auth(authorization)
    try:
        await client.mark_notification_read(auth, str(notification_id))
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.patch("/users/me/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    auth = _require_auth(authorization)
    try:
        await client.mark_all_notifications_read(auth)
    except HTTPStatusError as exc:
        raise _proxy_error(exc) from exc


@router.delete("/users/me/notifications", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_notifications(
    client: Annotated[UserServiceClient, Depends(get_user_client)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    auth = _require_auth(authorization)
    try:
        await client.clear_all_notifications(auth)
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
        "address_line": body.address_line,
        "postal_code": body.postal_code,
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
