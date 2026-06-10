"""Shared helpers for users tracking a custom community event."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from eventradar_common.event_ids import public_id_for

from user_app.db.models import UserEventReminder, UserSavedEvent

CUSTOM_PROVIDER = "custom"


def custom_event_public_id(event_id: uuid.UUID) -> int:
    return public_id_for(CUSTOM_PROVIDER, str(event_id))


def collect_users_tracking_custom_event(
    session: Session,
    event_id: uuid.UUID,
) -> set[uuid.UUID]:
    """Return user ids with favorites, enrolled, or reminders for this custom event."""
    external_id = str(event_id)
    public_event_id = custom_event_public_id(event_id)
    user_ids: set[uuid.UUID] = set()

    saved_filters = or_(
        UserSavedEvent.custom_event_id == event_id,
        and_(
            UserSavedEvent.provider == CUSTOM_PROVIDER,
            UserSavedEvent.external_id == external_id,
        ),
        and_(
            UserSavedEvent.provider == CUSTOM_PROVIDER,
            UserSavedEvent.public_event_id == public_event_id,
        ),
    )
    for row in session.scalars(select(UserSavedEvent).where(saved_filters)).all():
        user_ids.add(row.user_id)

    reminder_filters = or_(
        UserEventReminder.custom_event_id == event_id,
        and_(
            UserEventReminder.provider == CUSTOM_PROVIDER,
            UserEventReminder.external_id == external_id,
        ),
        and_(
            UserEventReminder.provider == CUSTOM_PROVIDER,
            UserEventReminder.public_event_id == public_event_id,
        ),
    )
    for row in session.scalars(select(UserEventReminder).where(reminder_filters)).all():
        user_ids.add(row.user_id)

    return user_ids
