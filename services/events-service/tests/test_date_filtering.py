from datetime import date
from unittest.mock import MagicMock, patch

import httpx

from events_app.domain.models import Event, MapPinCategory
from events_app.providers.protocol import ProviderSearchParams
from events_app.providers.ticketmaster.client import TicketmasterClient
from events_app.repositories.aggregator_repository import AggregatorEventRepository


def _make_tm_client() -> TicketmasterClient:
    return TicketmasterClient(
        api_key="test-key",
        base_url="https://example.com/discovery/v2",
        lat=50.047,
        lng=19.997,
        radius=50,
        unit="km",
        country_code="PL",
        locale="pl-pl",
        page_size=50,
        cache_ttl_seconds=60.0,
    )


def test_fetch_search_includes_start_and_end_datetime():
    client = _make_tm_client()
    params = ProviderSearchParams(
        date_from=date(2026, 6, 2),
        date_to=date(2026, 6, 8),
    )

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.json.return_value = {"_embedded": {"events": []}}

    mock_http = MagicMock()
    mock_http.get.return_value = mock_response

    with patch("events_app.providers.ticketmaster.client.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = mock_http
        client._fetch_search(params)

    query = mock_http.get.call_args.kwargs["params"]
    assert query["startDateTime"] == "2026-06-02T00:00:00Z"
    assert query["endDateTime"] == "2026-06-08T23:59:59Z"


class _StubProvider:
    name = "stub"

    def __init__(self, events: list[Event]) -> None:
        self._events = events

    def search_events(self, params: ProviderSearchParams) -> list[Event]:
        return list(self._events)

    def get_event(self, external_id: str) -> Event | None:
        return None


def _event_on(day: date, title: str) -> Event:
    return Event(
        id=hash(title) % 10_000,
        title=title,
        short_title=title,
        month=day.strftime("%b").upper(),
        day=str(day.day),
        time="8:00 PM",
        day_label=day.isoformat(),
        venue="Venue",
        location="Kraków",
        distance="1 km",
        category="Music",
        category_color="#7c3aed",
        price="$20",
        image="https://example.com/x.jpg",
        tags=("Music",),
        lat=50.0,
        lng=19.0,
        map_pin_category=MapPinCategory.MUSIC,
        featured=False,
        event_date=day,
        description="Desc",
        lineup=(),
        tickets=(),
    )


def test_aggregator_post_filters_by_date_range():
    from events_app.providers.id_registry import EventIdRegistry

    events = [
        _event_on(date(2026, 6, 1), "Before"),
        _event_on(date(2026, 6, 3), "Inside"),
        _event_on(date(2026, 6, 10), "After"),
    ]
    repo = AggregatorEventRepository([_StubProvider(events)], EventIdRegistry())

    results = repo.list_events(date_from=date(2026, 6, 2), date_to=date(2026, 6, 5))

    assert [event.title for event in results] == ["Inside"]
