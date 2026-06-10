from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from gateway.dto.events import EventDataDTO


class EventRefBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: int = Field(alias="eventId")
    community_event_id: str | None = Field(default=None, alias="communityEventId")


class EventTargetPayload(BaseModel):
    public_event_id: int
    provider: str
    external_id: str
    custom_event_id: UUID | None = None
    event_snapshot: dict | None = None

    def to_service_dict(self) -> dict:
        payload = {
            "public_event_id": self.public_event_id,
            "provider": self.provider,
            "external_id": self.external_id,
        }
        if self.custom_event_id is not None:
            payload["custom_event_id"] = str(self.custom_event_id)
        return payload


class EventActionStatusDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    favorited: bool = False
    enrolled: bool = False
    reminder_enabled: bool = Field(alias="reminderEnabled", default=False)


class ReminderBody(EventRefBody):
    enabled: bool
    starts_at: datetime | None = Field(default=None, alias="startsAt")


class NotificationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    type: str
    title: str
    body: str
    event_id: int | None = Field(default=None, alias="eventId")
    community_event_id: UUID | None = Field(default=None, alias="communityEventId")
    event_title: str | None = Field(default=None, alias="eventTitle")
    changed_fields: list[str] | None = Field(default=None, alias="changedFields")
    scheduled_for: datetime | None = Field(default=None, alias="scheduledFor")
    read: bool
    created_at: datetime = Field(alias="createdAt")


class NotificationsResponseDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[NotificationDTO]
    unread_count: int = Field(alias="unreadCount")


class SavedEventsListDTO(BaseModel):
    items: list[EventDataDTO]
