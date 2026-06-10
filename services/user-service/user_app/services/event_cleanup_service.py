"""Remove user references to a deleted custom event and notify affected users."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from user_app.db.models import UserEventReminder, UserSavedEvent
from user_app.services.custom_event_notifications import (
    clear_pending_event_notifications,
    notify_users_of_event_cancellation,
)
from user_app.services.custom_event_tracking import CUSTOM_PROVIDER, custom_event_public_id


def cleanup_custom_event_references(
    session: Session,
    *,
    event_id: uuid.UUID,
    event_title: str,
) -> None:
    """Delete favorites/enrolled/reminders and notify users who tracked this event."""
    external_id = str(event_id)
    public_event_id = custom_event_public_id(event_id)

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
        session.delete(row)

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
        session.delete(row)

    clear_pending_event_notifications(session, event_id=event_id)
    notify_users_of_event_cancellation(
        session,
        event_id=event_id,
        event_title=event_title,
    )
