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
    assert event.address_line == "4 Pennsylvania Plaza"
    assert event.postal_code == "10001"
    assert event.category == "Music"
    assert event.lat == 40.7505045
    assert event.lng == -73.9934387
    assert event.featured is True
    assert event.description == "A great night of live music."
    assert "$45" in event.price or "45" in event.price
    assert event.ticket_url == "https://www.ticketmaster.com/sample"
    assert event.provider == "ticketmaster"
    assert event.external_id == "vvG1VZKS5pr1qy"
    assert len(event.tickets) == 1
    assert event.tickets[0].url == event.ticket_url


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
    assert event.price == md.NO_PRICE
    assert event.ticket_url == ""


def test_map_without_price_ranges_uses_ticketmaster_link():
    event = map_ticketmaster_event(
        {
            "id": "pl-1",
            "name": "Kraków Concert",
            "url": "https://www.ticketmaster.pl/event/123",
        }
    )

    assert event.price == "See Ticketmaster"
    assert event.ticket_url == "https://www.ticketmaster.pl/event/123"
    assert len(event.tickets) == 1
    assert event.tickets[0].price == "See Ticketmaster"
    assert event.tickets[0].url == event.ticket_url


def test_map_polish_venue_address():
    event = map_ticketmaster_event(
        {
            "id": "pl-venue",
            "name": "Tauron Arena",
            "url": "https://www.ticketmaster.pl/event/1",
            "_embedded": {
                "venues": [
                    {
                        "name": "Tauron Arena Kraków",
                        "postalCode": "31-572",
                        "address": {"line1": "ul. Lema 7"},
                        "city": {"name": "Kraków"},
                        "country": {"name": "Poland", "countryCode": "PL"},
                    }
                ]
            },
        }
    )

    assert event.venue == "Tauron Arena Kraków"
    assert event.location == "Kraków, Poland"
    assert event.address_line == "ul. Lema 7"
    assert event.postal_code == "31-572"


def test_map_pln_price_range():
    event = map_ticketmaster_event(
        {
            "id": "pl-2",
            "name": "Local Show",
            "url": "https://www.ticketmaster.pl/event/456",
            "priceRanges": [{"type": "standard", "currency": "PLN", "min": 89, "max": 149}],
        }
    )

    assert event.price == "89 zł–149 zł"
    assert event.tickets[0].price == "89 zł–149 zł"
