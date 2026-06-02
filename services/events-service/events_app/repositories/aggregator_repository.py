from datetime import date

from events_app.domain.models import Category, Event
from events_app.providers.categories import DEFAULT_CATEGORIES
from events_app.providers.id_registry import EventIdRegistry
from events_app.providers.protocol import EventProvider, ProviderSearchParams


class AggregatorEventRepository:
    """Merges results from multiple EventProvider implementations."""

    def __init__(self, providers: list[EventProvider], registry: EventIdRegistry) -> None:
        self._providers = providers
        self._registry = registry
        self._provider_by_name = {provider.name: provider for provider in providers}

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
        params = ProviderSearchParams(
            category=category,
            location=location,
            date_from=date_from,
            date_to=date_to,
            query=query,
            sort=sort,
            lat=lat,
            lng=lng,
        )

        merged: list[Event] = []
        seen: set[int] = set()

        for provider in self._providers:
            for event in provider.search_events(params):
                if event.id in seen:
                    continue
                seen.add(event.id)
                merged.append(event)

        merged = _apply_client_filters(merged, category=category, location=location, query=query)
        return _sort_events(merged, sort)

    def get_event(self, event_id: int) -> Event | None:
        resolved = self._registry.resolve(event_id)
        if resolved:
            provider_name, external_id = resolved
            provider = self._provider_by_name.get(provider_name)
            if provider:
                return provider.get_event(external_id)

        for provider in self._providers:
            for event in provider.search_events(ProviderSearchParams()):
                if event.id == event_id:
                    return event

        return None

    def list_categories(self) -> list[Category]:
        return list(DEFAULT_CATEGORIES)


def _apply_client_filters(
    events: list[Event],
    *,
    category: str | None,
    location: str | None,
    query: str | None,
) -> list[Event]:
    results = events

    if category and category != "All Events":
        results = [event for event in results if event.category == category]

    if location:
        needle = location.lower()
        results = [
            event
            for event in results
            if needle in event.location.lower()
            or needle in event.venue.lower()
            or needle in event.title.lower()
        ]

    if query:
        needle = query.lower()
        results = [
            event
            for event in results
            if needle in event.title.lower()
            or needle in event.short_title.lower()
            or any(needle in tag.lower() for tag in event.tags)
        ]

    return results


def _sort_events(events: list[Event], sort: str) -> list[Event]:
    if sort == "date_desc":
        return sorted(events, key=lambda event: event.event_date, reverse=True)
    if sort == "price_asc":
        return sorted(events, key=lambda event: _price_sort_key(event.price))
    return sorted(events, key=lambda event: event.event_date)


def _price_sort_key(price: str) -> float:
    if price.lower() == "free":
        return 0.0
    if "no price" in price.lower():
        return 9999.0
    digits = "".join(ch for ch in price if ch.isdigit() or ch == ".")
    return float(digits) if digits else 9999.0
