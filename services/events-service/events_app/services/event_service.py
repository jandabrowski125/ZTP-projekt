from datetime import date

from events_app.domain.models import Category, Event
from events_app.repositories.protocol import EventRepository


class EventService:
    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

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
    ) -> list[Event]:
        return self._repository.list_events(
            category=category,
            location=location,
            date_from=date_from,
            date_to=date_to,
            query=query,
            sort=sort,
            lat=lat,
            lng=lng,
        )

    def get_event(self, event_id: int) -> Event:
        event = self._repository.get_event(event_id)
        if event is None:
            raise LookupError(f"Event {event_id} not found")
        return event

    def list_categories(self) -> list[Category]:
        return self._repository.list_categories()
