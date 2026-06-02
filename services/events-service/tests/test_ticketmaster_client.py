from unittest.mock import patch

import pytest

from events_app.providers.protocol import ProviderSearchParams
from events_app.providers.ticketmaster.client import (
    TicketmasterClient,
    TicketmasterRateLimitError,
    normalize_ticketmaster_locale,
    normalize_ticketmaster_unit,
)


def _make_client(**overrides: object) -> TicketmasterClient:
    defaults: dict[str, object] = {
        "api_key": "test-key",
        "base_url": "https://example.com/discovery/v2",
        "lat": 50.047,
        "lng": 19.997,
        "radius": 50,
        "unit": "km",
        "country_code": "PL",
        "locale": "pl-pl",
        "page_size": 50,
        "cache_ttl_seconds": 60.0,
    }
    defaults.update(overrides)
    return TicketmasterClient(**defaults)  # type: ignore[arg-type]

def test_normalize_unit_kilometers_to_km():
    assert normalize_ticketmaster_unit("kilometers") == "km"
    assert normalize_ticketmaster_unit("Kilometers") == "km"


def test_normalize_unit_miles():
    assert normalize_ticketmaster_unit("miles") == "miles"
    assert normalize_ticketmaster_unit("mi") == "miles"


def test_normalize_unit_km_unchanged():
    assert normalize_ticketmaster_unit("km") == "km"


def test_normalize_unit_invalid_raises():
    with pytest.raises(ValueError, match="Invalid Ticketmaster radius unit"):
        normalize_ticketmaster_unit("leagues")


def test_normalize_locale_lowercase():
    assert normalize_ticketmaster_locale("pl-PL") == "pl-pl"
    assert normalize_ticketmaster_locale("en-US") == "en-us"


def test_search_events_uses_cache_for_identical_params():
    client = _make_client()
    params = ProviderSearchParams(lat=50.046943, lng=19.997153)
    payload = [{"id": "evt-1", "name": "Test"}]

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
        side_effect=TicketmasterRateLimitError("429"),
    ):
        assert client.search_events(params) == payload


def test_search_events_returns_empty_on_rate_limit_without_cache():
    client = _make_client()
    params = ProviderSearchParams(lat=52.23, lng=21.01)

    with patch.object(
        client,
        "_fetch_search",
        side_effect=TicketmasterRateLimitError("429"),
    ):
        assert client.search_events(params) == []
