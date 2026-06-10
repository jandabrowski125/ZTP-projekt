from datetime import UTC, datetime

from events_app.providers.custom.provider import CustomEventProvider
from events_app.providers.id_registry import EventIdRegistry


def test_custom_event_time_uses_event_timezone_not_utc():
    provider = CustomEventProvider(client=None, registry=EventIdRegistry())  # type: ignore[arg-type]
    raw = {
        "id": "11111111-1111-1111-1111-111111111111",
        "title": "Kraków Night",
        "short_title": "Kraków Night",
        "venue": "Studio",
        "location": "Kraków, Poland",
        "lat": 50.0614,
        "lng": 19.9366,
        "category": "Music",
        "category_color": "#7c3aed",
        "price_label": "Free",
        "image_url": "",
        "tags": [],
        "starts_at": "2026-07-01T18:00:00+00:00",
        "event_timezone": "Europe/Warsaw",
        "owner_username": "host",
        "lineup": [],
        "tickets": [],
    }

    event = provider._map_to_event(raw)

    assert event.time == "8:00 PM"
    assert event.event_timezone == "Europe/Warsaw"
    assert event.starts_at == datetime(2026, 7, 1, 18, 0, tzinfo=UTC)
    assert event.event_date.isoformat() == "2026-07-01"
