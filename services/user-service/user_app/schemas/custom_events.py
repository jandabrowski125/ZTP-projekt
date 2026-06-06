from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_IMAGE_URL_LENGTH = 512_000


class CustomEventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    short_title: str | None = Field(default=None, max_length=80)
    description: str | None = None
    venue: str = Field(min_length=1, max_length=300)
    location: str = Field(min_length=1, max_length=300)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    category: str = Field(min_length=1, max_length=80)
    category_color: str = Field(default="#7c3aed", max_length=16)
    price_label: str | None = Field(default=None, max_length=64)
    image_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    starts_at: datetime
    ends_at: datetime | None = None
    lineup: list[dict] = Field(default_factory=list)
    tickets: list[dict] = Field(default_factory=list)
    publish: bool = False

    @field_validator("image_url")
    @classmethod
    def validate_image_url_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) > MAX_IMAGE_URL_LENGTH:
            msg = "Cover image is too large; use a smaller photo."
            raise ValueError(msg)
        return value


class CustomEventUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    short_title: str | None = Field(default=None, max_length=80)
    description: str | None = None
    venue: str | None = Field(default=None, min_length=1, max_length=300)
    location: str | None = Field(default=None, min_length=1, max_length=300)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    category_color: str | None = Field(default=None, max_length=16)
    price_label: str | None = Field(default=None, max_length=64)
    image_url: str | None = None
    tags: list[str] | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    lineup: list[dict] | None = None
    tickets: list[dict] | None = None
    publish: bool | None = None

    @field_validator("image_url")
    @classmethod
    def validate_image_url_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) > MAX_IMAGE_URL_LENGTH:
            msg = "Cover image is too large; use a smaller photo."
            raise ValueError(msg)
        return value


class CustomEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    owner_username: str | None = None
    title: str
    short_title: str | None
    description: str | None
    venue: str
    location: str
    lat: float
    lng: float
    category: str
    category_color: str
    price_label: str | None
    image_url: str | None
    tags: list
    starts_at: datetime
    ends_at: datetime | None
    status: str
    lineup: list
    tickets: list
