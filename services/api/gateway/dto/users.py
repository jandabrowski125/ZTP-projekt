from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPreferencesDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_reminders: bool = Field(alias="eventReminders", default=True)
    new_events: bool = Field(alias="newEvents", default=True)
    friend_activity: bool = Field(alias="friendActivity", default=False)
    promotions: bool = False
    private_profile: bool = Field(alias="privateProfile", default=False)


class UserProfileDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    email: EmailStr
    username: str
    full_name: str = Field(alias="fullName")
    bio: str | None = None
    location: str | None = None
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    preferences: UserPreferencesDTO


class TokenResponseDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    token_type: str = Field(alias="tokenType", default="bearer")


class UpdateProfileBody(BaseModel):
    full_name: str | None = Field(default=None, alias="fullName", max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = Field(default=None, alias="avatarUrl", max_length=2048)
    preferences: UserPreferencesDTO | None = None

    model_config = ConfigDict(populate_by_name=True)


class SavedEventDTO(BaseModel):
    """Ulubione lub minione wydarzenie zwracane frontendowi (camelCase)."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    list_type: str = Field(alias="listType")
    public_event_id: int | None = Field(default=None, alias="publicEventId")
    provider: str | None = None
    external_id: str | None = Field(default=None, alias="externalId")
    custom_event_id: UUID | None = Field(default=None, alias="customEventId")
    event_snapshot: dict | None = Field(default=None, alias="eventSnapshot")
    attended_at: date | None = Field(default=None, alias="attendedAt")


class SaveEventBody(BaseModel):
    """Ciało żądania POST /favorites lub POST /past-events (camelCase)."""

    model_config = ConfigDict(populate_by_name=True)

    public_event_id: int = Field(alias="publicEventId")
    provider: str = Field(max_length=32)
    external_id: str = Field(alias="externalId", max_length=128)
    event_snapshot: dict | None = Field(default=None, alias="eventSnapshot")
    attended_at: date | None = Field(default=None, alias="attendedAt")
