from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class MapPinCategory(StrEnum):
    MUSIC = "music"
    TECH = "tech"
    FOOD = "food"
    SPORTS = "sports"
    DEFAULT = "default"


@dataclass(frozen=True, slots=True)
class LineupArtist:
    name: str
    role: str
    role_color: str
    time: str


@dataclass(frozen=True, slots=True)
class Ticket:
    icon: str
    icon_color: str
    name: str
    sub: str
    price: str
    hover_color: str


@dataclass(frozen=True, slots=True)
class Event:
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
    tags: tuple[str, ...]
    lat: float
    lng: float
    map_pin_category: MapPinCategory
    featured: bool
    event_date: date
    description: str
    lineup: tuple[LineupArtist, ...]
    tickets: tuple[Ticket, ...]


@dataclass(frozen=True, slots=True)
class Category:
    label: str
    icon: str
