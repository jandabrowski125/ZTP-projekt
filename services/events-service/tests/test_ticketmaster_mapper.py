import json
from pathlib import Path

from events_app.providers import missing_data as md
from events_app.providers.ticketmaster.mapper import map_ticketmaster_event

FIXTURE = Path(__file__).parent / "fixtures" / "ticketmaster_event_search.json"


def test_map_ticketmaster_event_core_fields():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    event = map_ticketmaster_event(raw, featured=True)

    assert event.title == "Sample Concert"
    assert event.short_title == "Sample Concert"
    assert event.month == "MAR"
    assert event.day == "15"
    assert event.venue == "Madison Square Garden"
    assert "New York" in event.location
    assert event.category == "Music"
    assert event.lat == 40.7505045
    assert event.lng == -73.9934387
    assert event.featured is True
    assert event.description == "A great night of live music."
    assert "$45" in event.price or "45" in event.price


def test_map_ticketmaster_lineup_from_attractions():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    event = map_ticketmaster_event(raw)

    assert len(event.lineup) == 2
    assert event.lineup[0].name == "The Headliners"
    assert event.lineup[0].role == "Headliner"


def test_map_missing_fields_use_placeholders():
    event = map_ticketmaster_event({"id": "abc", "name": "Minimal Event"})

    assert event.title == "Minimal Event"
    assert event.venue == md.NO_VENUE
    assert event.location == md.NO_LOCATION
    assert event.image.startswith("https://")
