from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventTargetRequest(BaseModel):
    """Resolved event identity passed from the gateway."""

    public_event_id: int
    provider: str = Field(max_length=32)
    external_id: str = Field(max_length=128)
    custom_event_id: UUID | None = None
    event_snapshot: dict | None = None


class EventActionStatusResponse(BaseModel):
    favorited: bool = False
    enrolled: bool = False
    reminder_enabled: bool = False


class ReminderRequest(EventTargetRequest):
    enabled: bool
    starts_at: datetime | None = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    title: str
    body: str
    public_event_id: int | None
    community_event_id: UUID | None
    event_title: str | None = None
    changed_fields: list[str] | None = None
    scheduled_for: datetime
    read: bool
    created_at: datetime


class NotificationsListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
