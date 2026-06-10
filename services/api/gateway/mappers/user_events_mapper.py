from typing import Any

from gateway.dto.user_events import EventActionStatusDTO, NotificationDTO


def to_event_action_status_dto(raw: dict[str, Any]) -> EventActionStatusDTO:
    return EventActionStatusDTO(
        favorited=bool(raw.get("favorited")),
        enrolled=bool(raw.get("enrolled")),
        reminderEnabled=bool(raw.get("reminder_enabled")),
    )


def to_notification_dto(raw: dict[str, Any]) -> NotificationDTO:
    return NotificationDTO(
        id=raw["id"],
        type=raw["type"],
        title=raw["title"],
        body=raw["body"],
        eventId=raw.get("public_event_id"),
        communityEventId=raw.get("community_event_id"),
        eventTitle=raw.get("event_title"),
        changedFields=raw.get("changed_fields"),
        scheduledFor=raw.get("scheduled_for"),
        read=bool(raw.get("read")),
        createdAt=raw["created_at"],
    )
