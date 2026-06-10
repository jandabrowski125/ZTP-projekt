import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from user_app.api.deps import get_current_user, get_user_repository
from user_app.db.models import SavedEventListType, User
from user_app.db.session import get_db
from user_app.repositories.notification_repository import NotificationRepository
from user_app.repositories.user_repository import UserRepository
from user_app.schemas.user_events import (
    EventActionStatusResponse,
    EventTargetRequest,
    NotificationResponse,
    NotificationsListResponse,
    ReminderRequest,
)
from user_app.services import reminder_service

router = APIRouter(prefix="/internal/v1")


def get_notification_repository(
    db: Annotated[Session, Depends(get_db)],
) -> NotificationRepository:
    return NotificationRepository(db)


def _event_title(target: EventTargetRequest) -> str:
    snapshot = target.event_snapshot or {}
    return str(snapshot.get("title") or snapshot.get("short_title") or "Event")


def _resolve_starts_at(target: EventTargetRequest, provided: datetime | None) -> datetime:
    if provided is not None:
        return provided if provided.tzinfo else provided.replace(tzinfo=UTC)

    snapshot = target.event_snapshot or {}
    raw = snapshot.get("starts_at") or snapshot.get("event_date")
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    if isinstance(raw, str):
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Event start time is required for reminders",
    )


@router.get("/users/me/event-actions", response_model=EventActionStatusResponse)
def get_event_action_status(
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    db: Annotated[Session, Depends(get_db)],
    public_event_id: int = Query(alias="publicEventId"),
    provider: str = Query(),
    external_id: str = Query(alias="externalId"),
    community_event_id: uuid.UUID | None = Query(default=None, alias="communityEventId"),
) -> EventActionStatusResponse:
    target = EventTargetRequest(
        public_event_id=public_event_id,
        provider=provider,
        external_id=external_id,
        custom_event_id=community_event_id,
    )
    return EventActionStatusResponse(
        favorited=repo.has_saved_event(current_user.id, SavedEventListType.FAVORITE, target),
        enrolled=repo.has_saved_event(current_user.id, SavedEventListType.ENROLLED, target),
        reminder_enabled=reminder_service.has_active_reminder(db, current_user.id, target),
    )


@router.put("/users/me/favorites", status_code=status.HTTP_204_NO_CONTENT)
def upsert_favorite(
    body: EventTargetRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    repo.add_saved_event(
        user_id=current_user.id,
        list_type=SavedEventListType.FAVORITE,
        target=body,
    )


@router.delete("/users/me/favorites", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_by_ref(
    body: EventTargetRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    if not repo.remove_saved_event_by_ref(current_user.id, SavedEventListType.FAVORITE, body):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.put("/users/me/enrolled", status_code=status.HTTP_204_NO_CONTENT)
def upsert_enrolled(
    body: EventTargetRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    repo.add_saved_event(
        user_id=current_user.id,
        list_type=SavedEventListType.ENROLLED,
        target=body,
    )


@router.delete("/users/me/enrolled", status_code=status.HTTP_204_NO_CONTENT)
def remove_enrolled_by_ref(
    body: EventTargetRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> None:
    if not repo.remove_saved_event_by_ref(current_user.id, SavedEventListType.ENROLLED, body):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/users/me/enrolled", response_model=list)
def list_enrolled(
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
):
    from user_app.schemas.users import SavedEventResponse

    rows = repo.list_saved_events(current_user.id, SavedEventListType.ENROLLED)
    return [SavedEventResponse.model_validate(row) for row in rows]


@router.put("/users/me/reminders", status_code=status.HTTP_204_NO_CONTENT)
def set_event_reminder(
    body: ReminderRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    target = EventTargetRequest(
        public_event_id=body.public_event_id,
        provider=body.provider,
        external_id=body.external_id,
        custom_event_id=body.custom_event_id,
        event_snapshot=body.event_snapshot,
    )
    if body.enabled:
        starts_at = _resolve_starts_at(target, body.starts_at)
        reminder_service.enable_reminder(
            db,
            current_user.id,
            target,
            starts_at=starts_at,
            event_title=_event_title(target),
        )
    else:
        reminder_service.disable_reminder(db, current_user.id, target)


@router.get("/users/me/notifications", response_model=NotificationsListResponse)
def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    notif_repo: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> NotificationsListResponse:
    items = notif_repo.list_for_user(current_user.id)
    return NotificationsListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        unread_count=notif_repo.unread_count(current_user.id),
    )


@router.patch("/users/me/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    notif_repo: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> None:
    if not notif_repo.mark_read(current_user.id, notification_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.patch("/users/me/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_user)],
    notif_repo: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> None:
    notif_repo.mark_all_read(current_user.id)


@router.delete("/users/me/notifications", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    notif_repo: Annotated[NotificationRepository, Depends(get_notification_repository)],
) -> None:
    notif_repo.delete_all_for_user(current_user.id)
