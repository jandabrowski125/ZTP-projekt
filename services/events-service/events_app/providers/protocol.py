from dataclasses import dataclass
from datetime import date
from typing import Protocol

from events_app.domain.models import Event


@dataclass(frozen=True, slots=True)
class ProviderSearchParams:
    category: str | None = None
    location: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    query: str | None = None
    sort: str = "date_asc"
    lat: float | None = None
    lng: float | None = None


class EventProvider(Protocol):
    """External event source (Ticketmaster, Eventim, …)."""

    @property
    def name(self) -> str: ...

    def search_events(self, params: ProviderSearchParams) -> list[Event]: ...

    def get_event(self, external_id: str) -> Event | None: ...
