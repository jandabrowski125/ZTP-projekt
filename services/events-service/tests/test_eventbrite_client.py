from datetime import date
from unittest.mock import MagicMock, patch

from events_app.providers.eventbrite.client import (
    EventbriteClient,
    EventbriteRateLimitError,
    EventbriteSearchUnavailableError,
    format_location_within,
    normalize_eventbrite_unit,
)
from events_app.providers.protocol import ProviderSearchParams


def _make_client(**overrides: object) -> EventbriteClient:
    defaults: dict[str, object] = {
        "token": "test-token",
        "base_url": "https://www.eventbriteapi.com/v3",
        "lat": 50.047,
        "lng": 19.997,
        "radius": 50,
        "unit": "km",
        "page_size": 50,
        "cache_ttl_seconds": 60.0,
    }
    defaults.update(overrides)
    return EventbriteClient(**defaults)  # type: ignore[arg-type]


def test_normalize_unit_kilometers_to_km():
    assert normalize_eventbrite_unit("kilometers") == "km"


def test_format_location_within():
    assert format_location_within(50, "km") == "50km"


def test_search_events_uses_cache_for_identical_params():
    client = _make_client()
    params = ProviderSearchParams(lat=50.046943, lng=19.997153)
    payload = [{"id": "evt-1", "name": {"text": "Test"}}]

    with patch.object(client, "_fetch_search", return_value=payload) as fetch:
        assert client.search_events(params) == payload
        assert client.search_events(params) == payload
        fetch.assert_called_once()


def test_search_events_serves_stale_on_rate_limit():
    client = _make_client()
    params = ProviderSearchParams(lat=50.046943, lng=19.997153)
    payload = [{"id": "evt-1"}]

    with patch.object(client, "_fetch_search", return_value=payload):
        assert client.search_events(params) == payload

    with patch.object(
        client,
        "_fetch_search",
        side_effect=EventbriteRateLimitError("429"),
    ):
        assert client.search_events(params) == payload


def test_search_uses_organization_when_configured():
    client = _make_client(organization_id="org-99")
    params = ProviderSearchParams(lat=50.05, lng=19.99)
    org_events = [{"id": "org-1"}]

    with patch.object(client, "_fetch_organization_events", return_value=org_events) as org_fetch, patch.object(
        client, "_fetch_search"
    ) as search_fetch:
        assert client.search_events(params) == org_events
        org_fetch.assert_called_once_with(params)
        search_fetch.assert_not_called()


def test_search_falls_back_to_empty_on_404_without_organization():
    client = _make_client()
    params = ProviderSearchParams(lat=52.23, lng=21.01)

    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 404
    mock_response.text = '{"error":"NOT_FOUND"}'
    mock_response.request.url = "https://www.eventbriteapi.com/v3/events/search/"

    with patch("httpx.Client") as client_cls:
        http = MagicMock()
        client_cls.return_value.__enter__.return_value = http
        http.get.return_value = mock_response
        assert client.search_events(params) == []


def test_search_returns_empty_on_406_without_organization():
    client = _make_client()
    params = ProviderSearchParams(lat=52.23, lng=21.01)

    with patch.object(
        client,
        "_fetch_search",
        side_effect=EventbriteSearchUnavailableError("406"),
    ):
        assert client.search_events(params) == []


def test_fetch_organization_events_uses_yyyy_mm_dd_dates():
    client = _make_client(organization_id="org-99")
    params = ProviderSearchParams(
        lat=50.05,
        lng=19.99,
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
    )

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"events": []}

    with patch("httpx.Client") as client_cls:
        http = MagicMock()
        client_cls.return_value.__enter__.return_value = http
        http.get.return_value = mock_response

        client._fetch_organization_events(params)

    query = http.get.call_args.kwargs["params"]
    assert query["start_date.range_start"] == "2026-04-01"
    assert query["start_date.range_end"] == "2026-04-30"


def test_fetch_search_builds_geo_and_date_query():
    client = _make_client()
    params = ProviderSearchParams(
        lat=50.05,
        lng=19.99,
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
        query="jazz",
        category="Music",
    )

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"events": [{"id": "1"}]}

    with patch("httpx.Client") as client_cls:
        http = MagicMock()
        client_cls.return_value.__enter__.return_value = http
        http.get.return_value = mock_response

        events = client._fetch_search(params)

    assert events == [{"id": "1"}]
    call_kwargs = http.get.call_args.kwargs
    query = call_kwargs["params"]
    assert query["location.latitude"] == "50.05"
    assert query["location.longitude"] == "19.99"
    assert query["location.within"] == "50km"
    assert query["q"] == "jazz"
    assert query["categories"] == "103"
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-token"
