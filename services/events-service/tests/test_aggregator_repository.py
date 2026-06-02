from datetime import date

from events_app.domain.models import Event, MapPinCategory
from events_app.providers.id_registry import EventIdRegistry, public_id_for
from events_app.providers.protocol import ProviderSearchParams
from events_app.repositories.aggregator_repository import AggregatorEventRepository


class _StubProvider:
    name = "stub"

    def __init__(self, events: list[Event]) -> None:
        self._events = events

    def search_events(self, params: ProviderSearchParams) -> list[Event]:
        return list(self._events)

    def get_event(self, external_id: str) -> Event | None:
        return next((e for e in self._events if external_id == "ext-1"), None)


def _sample_event(event_id: int, title: str, category: str = "Music") -> Event:
    return Event(
        id=event_id,
        title=title,
        short_title=title,
        month="MAR",
        day="1",
        time="8:00 PM",
        day_label="Mar 1",
        venue="Venue A",
        location="Brooklyn, NY",
        distance="1 mi",
        category=category,
        category_color="#7c3aed",
        price="$20",
        image="https://example.com/x.jpg",
        tags=("Music",),
        lat=40.7,
        lng=-74.0,
        map_pin_category=MapPinCategory.MUSIC,
        featured=False,
        event_date=date(2026, 3, 1),
        description="Desc",
        lineup=(),
        tickets=(),
    )


def test_aggregator_merges_providers_deduplicates_by_id():
    registry = EventIdRegistry()
    event_a = _sample_event(101, "Event A")
    event_b = _sample_event(202, "Event B")

    repo = AggregatorEventRepository(
        [_StubProvider([event_a]), _StubProvider([event_a, event_b])],
        registry,
    )

    results = repo.list_events()
    assert len(results) == 2
    assert {event.title for event in results} == {"Event A", "Event B"}


def test_aggregator_resolves_get_event_via_registry():
    registry = EventIdRegistry()
    registry.register("stub", "ext-1", 999)
    event = _sample_event(999, "Registered")
    provider = _StubProvider([event])

    repo = AggregatorEventRepository([provider], registry)
    found = repo.get_event(999)

    assert found is not None
    assert found.title == "Registered"


def test_public_id_is_deterministic():
    assert public_id_for("ticketmaster", "vvG1") == public_id_for("ticketmaster", "vvG1")
