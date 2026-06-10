"""In-app notifications for custom event lifecycle (cancelled, updated)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from user_app.db.models import (
    CustomEvent,
    NotificationType,
    UserNotification,
)
from user_app.services.custom_event_tracking import (
    collect_users_tracking_custom_event,
    custom_event_public_id,
)
from user_app.services.event_change_fields import EventChangeField, detect_custom_event_changes

CUSTOM_PROVIDER = "custom"


@dataclass(frozen=True)
class CustomEventSnapshot:
    title: str
    venue: str
    location: str
    address_line: str | None
    postal_code: str | None
    lat: float
    lng: float
    description: str | None
    price_label: str | None
    image_url: str | None
    category: str
    category_color: str
    tickets: list
    starts_at: datetime


def snapshot_custom_event(event: CustomEvent) -> CustomEventSnapshot:
    """Capture scalar event state before applying an update."""
    return CustomEventSnapshot(
        title=event.title,
        venue=event.venue,
        location=event.location,
        address_line=event.address_line,
        postal_code=event.postal_code,
        lat=event.lat,
        lng=event.lng,
        description=event.description,
        price_label=event.price_label,
        image_url=event.image_url,
        category=event.category,
        category_color=event.category_color,
        tickets=list(event.tickets or []),
        starts_at=event.starts_at,
    )


def notify_users_of_event_cancellation(
    session: Session,
    *,
    event_id: uuid.UUID,
    event_title: str,
) -> None:
    """Notify every user who tracked this event that it was cancelled."""
    now = datetime.now(UTC)
    affected_user_ids = collect_users_tracking_custom_event(session, event_id)
    body = (
        f'"{event_title}" has been cancelled by the organizer. '
        "Head to Explore to discover other events near you."
    )
    for user_id in affected_user_ids:
        session.add(
            UserNotification(
                user_id=user_id,
                type=NotificationType.SYSTEM,
                title="Event cancelled",
                body=body,
                scheduled_for=now,
                read=False,
            )
        )


def _update_notification_body(changed_fields: list[EventChangeField]) -> str:
    labels = {
        "title": "title",
        "date": "date",
        "time": "time",
        "location": "location",
        "venue": "venue",
        "description": "description",
        "price": "price",
        "image": "image",
        "category": "category",
        "tickets": "tickets",
    }
    unique_fields = list(dict.fromkeys(changed_fields))
    field_labels = [labels.get(field, field) for field in unique_fields]
    if not field_labels:
        return "Event details have been updated."
    if len(field_labels) == 1:
        joined = field_labels[0]
        verb = "has"
    elif len(field_labels) == 2:
        joined = f"{field_labels[0]} and {field_labels[1]}"
        verb = "have"
    else:
        joined = f"{', '.join(field_labels[:-1])}, and {field_labels[-1]}"
        verb = "have"
    return f"The {joined} {verb} been changed."


def notify_users_of_event_update(
    session: Session,
    *,
    event: CustomEvent,
    changed_fields: list[EventChangeField],
) -> None:
    """Notify every user who tracked this event that details changed."""
    if not changed_fields:
        return

    now = datetime.now(UTC)
    public_event_id = custom_event_public_id(event.id)
    affected_user_ids = collect_users_tracking_custom_event(session, event.id)
    body = _update_notification_body(changed_fields)

    for user_id in affected_user_ids:
        session.add(
            UserNotification(
                user_id=user_id,
                type=NotificationType.EVENT_UPDATED,
                title="Event updated",
                body=body,
                public_event_id=public_event_id,
                community_event_id=event.id,
                event_title=event.title,
                changed_fields=list(changed_fields),
                scheduled_for=now,
                read=False,
            )
        )


def clear_pending_event_notifications(
    session: Session,
    *,
    event_id: uuid.UUID,
) -> None:
    """Remove reminder/update notifications tied to a deleted custom event."""
    public_event_id = custom_event_public_id(event_id)
    notification_filters = or_(
        UserNotification.community_event_id == event_id,
        and_(
            UserNotification.public_event_id == public_event_id,
            UserNotification.type == NotificationType.EVENT_REMINDER,
        ),
    )
    for row in session.scalars(select(UserNotification).where(notification_filters)).all():
        session.delete(row)
