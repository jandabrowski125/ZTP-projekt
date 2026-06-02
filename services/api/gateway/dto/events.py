"""Public API DTOs aligned with Tpfeventradar frontend (camelCase JSON)."""

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


class EventDetailsDTO(EventDataDTO):
    description: str
    lineup: list[LineupArtistDTO] = Field(default_factory=list)
    tickets: list[TicketDTO] = Field(default_factory=list)


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
