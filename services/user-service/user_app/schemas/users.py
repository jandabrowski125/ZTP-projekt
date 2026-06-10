from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MAX_AVATAR_URL_LENGTH = 512_000


class UserPreferences(BaseModel):
    event_reminders: bool = True
    new_events: bool = True
    friend_activity: bool = False
    promotions: bool = False
    private_profile: bool = False


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str | None = Field(default=None, max_length=128)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    full_name: str = Field(min_length=1, max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = None
    preferences: UserPreferences | None = None

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) > MAX_AVATAR_URL_LENGTH:
            msg = "Profile photo is too large; use a smaller image."
            raise ValueError(msg)
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: str
    full_name: str
    bio: str | None
    location: str | None
    avatar_url: str | None
    preferences: UserPreferences
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = None
    preferences: UserPreferences | None = None

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) > MAX_AVATAR_URL_LENGTH:
            msg = "Profile photo is too large; use a smaller image."
            raise ValueError(msg)
        return value


class SaveAggregatedEventRequest(BaseModel):
    public_event_id: int
    provider: str = Field(max_length=32)
    external_id: str = Field(max_length=128)
    event_snapshot: dict | None = None
    attended_at: date | None = None


class SavedEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    list_type: str
    public_event_id: int | None
    provider: str | None
    external_id: str | None
    custom_event_id: UUID | None
    event_snapshot: dict | None
    attended_at: date | None
