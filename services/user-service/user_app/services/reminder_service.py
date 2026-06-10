from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from eventradar_common.event_ids import public_id_for

from user_app.db.models import CustomEvent, NotificationType, UserEventReminder, UserNotification
from user_app.schemas.user_events import EventTargetRequest

CUSTOM_PROVIDER = "custom"

REMINDER_OFFSETS: tuple[tuple[timedelta, str], ...] = (
    (timedelta(hours=24), "Event starts in 24 hours"),
    (timedelta(hours=6), "Event starts in 6 hours"),
    (timedelta(hours=1), "Event starts in 1 hour"),
)


def _now() -> datetime:
    return datetime.now(UTC)


def _event_key_filter(
    user_id: uuid.UUID,
    target: EventTargetRequest,
):
    if target.custom_event_id is not None:
        return (
            UserEventReminder.user_id == user_id,
            UserEventReminder.custom_event_id == target.custom_event_id,
        )
    return (
        UserEventReminder.user_id == user_id,
        UserEventReminder.public_event_id == target.public_event_id,
        UserEventReminder.provider == target.provider,
        UserEventReminder.external_id == target.external_id,
    )


def _notification_key_filter(
    user_id: uuid.UUID,
    target: EventTargetRequest,
):
    if target.custom_event_id is not None:
        return (
            UserNotification.user_id == user_id,
            UserNotification.community_event_id == target.custom_event_id,
            UserNotification.type == NotificationType.EVENT_REMINDER,
        )
    return (
        UserNotification.user_id == user_id,
        UserNotification.public_event_id == target.public_event_id,
        UserNotification.type == NotificationType.EVENT_REMINDER,
    )


def has_active_reminder(session: Session, user_id: uuid.UUID, target: EventTargetRequest) -> bool:
    stmt = select(UserEventReminder).where(*_event_key_filter(user_id, target))
    return session.scalars(stmt).first() is not None


def disable_reminder(session: Session, user_id: uuid.UUID, target: EventTargetRequest) -> None:
    for row in session.scalars(select(UserEventReminder).where(*_event_key_filter(user_id, target))).all():
        session.delete(row)

    for row in session.scalars(select(UserNotification).where(*_notification_key_filter(user_id, target))).all():
        session.delete(row)
    session.commit()


def _schedule_reminder_notifications(
    session: Session,
    user_id: uuid.UUID,
    target: EventTargetRequest,
    *,
    starts_at: datetime,
    event_title: str,
) -> None:
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    else:
        starts_at = starts_at.astimezone(UTC)

    now = _now()
    for offset, title in REMINDER_OFFSETS:
        scheduled_for = starts_at - offset
        if scheduled_for <= now:
            continue
        session.add(
            UserNotification(
                user_id=user_id,
                type=NotificationType.EVENT_REMINDER,
                title=title,
                body=event_title,
                public_event_id=target.public_event_id,
                community_event_id=target.custom_event_id,
                scheduled_for=scheduled_for,
                read=False,
            )
        )


def enable_reminder(
    session: Session,
    user_id: uuid.UUID,
    target: EventTargetRequest,
    *,
    starts_at: datetime,
    event_title: str,
) -> None:
    disable_reminder(session, user_id, target)

    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    else:
        starts_at = starts_at.astimezone(UTC)

    session.add(
        UserEventReminder(
            user_id=user_id,
            public_event_id=target.public_event_id,
            provider=target.provider,
            external_id=target.external_id,
            custom_event_id=target.custom_event_id,
            event_title=event_title,
            event_starts_at=starts_at,
        )
    )
    _schedule_reminder_notifications(
        session,
        user_id,
        target,
        starts_at=starts_at,
        event_title=event_title,
    )

    session.commit()


def refresh_custom_event_reminders(session: Session, event: CustomEvent) -> None:
    """Reschedule pending reminder notifications after event time or title changes."""
    external_id = str(event.id)
    public_event_id = public_id_for(CUSTOM_PROVIDER, external_id)
    reminder_filters = or_(
        UserEventReminder.custom_event_id == event.id,
        and_(
            UserEventReminder.provider == CUSTOM_PROVIDER,
            UserEventReminder.external_id == external_id,
        ),
        and_(
            UserEventReminder.provider == CUSTOM_PROVIDER,
            UserEventReminder.public_event_id == public_event_id,
        ),
    )

    for reminder in session.scalars(select(UserEventReminder).where(reminder_filters)).all():
        target = EventTargetRequest(
            public_event_id=public_event_id,
            provider=CUSTOM_PROVIDER,
            external_id=external_id,
            custom_event_id=event.id,
        )
        for row in session.scalars(
            select(UserNotification).where(*_notification_key_filter(reminder.user_id, target))
        ).all():
            session.delete(row)

        reminder.event_title = event.title
        reminder.event_starts_at = event.starts_at
        _schedule_reminder_notifications(
            session,
            reminder.user_id,
            target,
            starts_at=event.starts_at,
            event_title=event.title,
        )
