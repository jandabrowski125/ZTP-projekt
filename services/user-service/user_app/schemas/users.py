from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from user_app.validation import validate_strong_password


class UserPreferences(BaseModel):
    event_reminders: bool = True
    new_events: bool = True
    friend_activity: bool = False
    promotions: bool = False
    private_profile: bool = False


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    full_name: str = Field(min_length=1, max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = Field(default=None, max_length=2048)
    preferences: UserPreferences | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_strong_password(value)


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


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = Field(default=None, max_length=2048)
    preferences: UserPreferences | None = None


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
