from datetime import date

from events_app.domain.models import Event, MapPinCategory
from events_app.providers.id_registry import EventIdRegistry, public_id_for
from events_app.providers.protocol import ProviderSearchParams
from events_app.repositories.aggregator_repository import AggregatorEventRepository


class _StubProvider:
    def __init__(self, events: list[Event], *, name: str = "stub", fail: bool = False) -> None:
        self.name = name
        self._events = events
        self._fail = fail

    def search_events(self, params: ProviderSearchParams) -> list[Event]:
        if self._fail:
            raise RuntimeError("provider unavailable")
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


def test_aggregator_continues_when_one_provider_fails():
    registry = EventIdRegistry()
    ok_event = _sample_event(101, "Ticketmaster Event")
    failing = _StubProvider([], name="eventbrite", fail=True)
    working = _StubProvider([ok_event], name="ticketmaster")

    repo = AggregatorEventRepository([failing, working], registry)
    results = repo.list_events()

    assert len(results) == 1
    assert results[0].title == "Ticketmaster Event"


def test_aggregator_excludes_custom_provider_when_community_disabled():
    registry = EventIdRegistry()
    custom_event = _sample_event(301, "Community Meetup")
    custom_event = Event(
        id=custom_event.id,
        title=custom_event.title,
        short_title=custom_event.short_title,
        month=custom_event.month,
        day=custom_event.day,
        time=custom_event.time,
        day_label=custom_event.day_label,
        venue=custom_event.venue,
        location=custom_event.location,
        distance=custom_event.distance,
        category=custom_event.category,
        category_color=custom_event.category_color,
        price=custom_event.price,
        image=custom_event.image,
        tags=custom_event.tags,
        lat=custom_event.lat,
        lng=custom_event.lng,
        map_pin_category=custom_event.map_pin_category,
        featured=custom_event.featured,
        event_date=custom_event.event_date,
        description=custom_event.description,
        lineup=custom_event.lineup,
        tickets=custom_event.tickets,
        is_community_event=True,
        created_by="alice",
    )
    ticketmaster_event = _sample_event(101, "Ticketmaster Event")

    repo = AggregatorEventRepository(
        [
            _StubProvider([custom_event], name="custom"),
            _StubProvider([ticketmaster_event], name="ticketmaster"),
        ],
        registry,
    )

    without = repo.list_events(include_community=False)
    assert len(without) == 1
    assert without[0].title == "Ticketmaster Event"

    with_community = repo.list_events(include_community=True)
    assert len(with_community) == 2


def test_public_id_is_deterministic():
    assert public_id_for("ticketmaster", "vvG1") == public_id_for("ticketmaster", "vvG1")
