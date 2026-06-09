"""Public API DTOs aligned with Tpfeventradar frontend (camelCase JSON)."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class EventDataDTO(BaseModel):
    """Matches frontend `EventData` in dashboard/events.ts."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    title: str
    short_title: str = Field(alias="shortTitle")
    month: str
    day: str
    time: str
    day_label: str = Field(alias="dayLabel")
    venue: str
    location: str
    address_line: str = Field(default="", alias="addressLine")
    postal_code: str = Field(default="", alias="postalCode")
    distance: str
    category: str
    category_color: str = Field(alias="categoryColor")
    price: str
    image: str
    tags: list[str]


class LineupArtistDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    role: str
    role_color: str = Field(alias="roleColor")
    time: str


class TicketDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    icon: str
    icon_color: str = Field(alias="iconColor")
    name: str
    sub: str
    price: str
    hover_color: str = Field(alias="hoverColor")
    url: str = ""


class EventDetailsDTO(EventDataDTO):
    description: str
    lineup: list[LineupArtistDTO] = Field(default_factory=list)
    tickets: list[TicketDTO] = Field(default_factory=list)
    ticket_url: str = Field(default="", alias="ticketUrl")
    provider: str = ""
    external_id: str = Field(default="", alias="externalId")
    is_community_event: bool = Field(default=False, alias="isCommunityEvent")
    created_by: str | None = Field(default=None, alias="createdBy")
    community_event_id: str | None = Field(default=None, alias="communityEventId")


class MapPinDTO(BaseModel):
    """Matches frontend `MapPin` in EventMap.tsx."""

    id: int
    lat: float
    lng: float
    label: str
    time: str
    price: str
    category: str
    featured: bool | None = None


class CategoryDTO(BaseModel):
    label: str
    icon: str


class EventsListResponseDTO(BaseModel):
    items: list[EventDataDTO]
    total: int


class CustomEventCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    short_title: str | None = Field(default=None, alias="shortTitle")
    description: str | None = None
    venue: str
    location: str
    address_line: str | None = Field(default=None, alias="addressLine")
    postal_code: str | None = Field(default=None, alias="postalCode")
    lat: float
    lng: float
    category: str
    category_color: str = Field(default="#7c3aed", alias="categoryColor")
    price_label: str | None = Field(default=None, alias="priceLabel")
    image_url: str | None = Field(default=None, alias="imageUrl")
    tags: list[str] = Field(default_factory=list)
    starts_at: datetime = Field(alias="startsAt")
    ends_at: datetime | None = Field(default=None, alias="endsAt")
    lineup: list[dict] = Field(default_factory=list)
    tickets: list[dict] = Field(default_factory=list)
    publish: bool = False


class CustomEventUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    short_title: str | None = Field(default=None, alias="shortTitle")
    description: str | None = None
    venue: str | None = None
    location: str | None = None
    address_line: str | None = Field(default=None, alias="addressLine")
    postal_code: str | None = Field(default=None, alias="postalCode")
    lat: float | None = None
    lng: float | None = None
    category: str | None = None
    category_color: str | None = Field(default=None, alias="categoryColor")
    price_label: str | None = Field(default=None, alias="priceLabel")
    image_url: str | None = Field(default=None, alias="imageUrl")
    tags: list[str] | None = None
    starts_at: datetime | None = Field(default=None, alias="startsAt")
    ends_at: datetime | None = Field(default=None, alias="endsAt")
    lineup: list[dict] | None = None
    tickets: list[dict] | None = None
    publish: bool | None = None


class CustomEventResponseDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    owner_user_id: str = Field(alias="ownerUserId")
    owner_username: str | None = Field(default=None, alias="ownerUsername")
    title: str
    short_title: str | None = Field(default=None, alias="shortTitle")
    description: str | None = None
    venue: str
    location: str
    address_line: str | None = Field(default=None, alias="addressLine")
    postal_code: str | None = Field(default=None, alias="postalCode")
    lat: float
    lng: float
    category: str
    category_color: str = Field(alias="categoryColor")
    price_label: str | None = Field(default=None, alias="priceLabel")
    image_url: str | None = Field(default=None, alias="imageUrl")
    tags: list = Field(default_factory=list)
    starts_at: str = Field(alias="startsAt")
    ends_at: str | None = Field(default=None, alias="endsAt")
    status: str
    lineup: list = Field(default_factory=list)
    tickets: list = Field(default_factory=list)
