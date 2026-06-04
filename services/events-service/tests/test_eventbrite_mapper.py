import json
from pathlib import Path

from events_app.providers.eventbrite.mapper import map_eventbrite_event

FIXTURE = Path(__file__).parent / "fixtures" / "eventbrite_organization_events.json"


def test_map_eventbrite_event_produces_event_fields():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))["events"][0]
    event = map_eventbrite_event(
        raw,
        provider="eventbrite",
        search_lat=50.046943,
        search_lng=19.997153,
    )

    assert event.title == "Kraków Jazz Night"
    assert event.category == "Music"
    assert event.lat > 0
    assert event.lng > 0
    assert "Eventbrite" in event.tags
    assert event.month == "JUN"
    assert event.day == "15"
