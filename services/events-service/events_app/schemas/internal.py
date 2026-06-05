from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class LineupArtistSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    role: str
    role_color: str
    time: str


class TicketSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    icon: str
    icon_color: str
    name: str
    sub: str
    price: str
    hover_color: str


class EventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    short_title: str
    month: str
    day: str
    time: str
    day_label: str
    venue: str
    location: str
    distance: str
    category: str
    category_color: str
    price: str
    image: str
    tags: list[str]
    lat: float
    lng: float
    map_pin_category: str
    featured: bool
    event_date: date
    description: str
    lineup: list[LineupArtistSchema] = Field(default_factory=list)
    tickets: list[TicketSchema] = Field(default_factory=list)
    is_community_event: bool = False
    created_by: str | None = None


class CategorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    icon: str
