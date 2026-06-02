from datetime import date
from typing import Protocol

from events_app.domain.models import Category, Event


class EventRepository(Protocol):
    def list_events(
        self,
        *,
        category: str | None = None,
        location: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        query: str | None = None,
        sort: str = "date_asc",
        lat: float | None = None,
        lng: float | None = None,
    ) -> list[Event]: ...

    def get_event(self, event_id: int) -> Event | None: ...

    def list_categories(self) -> list[Category]: ...
