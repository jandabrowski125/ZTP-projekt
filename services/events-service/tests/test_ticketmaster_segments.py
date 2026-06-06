"""Tests for Ticketmaster segment ID → category mapping."""

from events_app.providers.ticketmaster.mapper import map_ticketmaster_event


def test_segment_id_maps_music_regardless_of_localized_name():
    raw = {
        "id": "evt-pl",
        "name": "Koncert",
        "classifications": [
            {
                "primary": True,
                "segment": {"id": "KZFzniwnSyZfZ7v7nJ", "name": "Muzyka"},
            }
        ],
    }
    assert map_ticketmaster_event(raw).category == "Music"


def test_segment_id_maps_other_from_miscellaneous():
    raw = {
        "id": "evt-other",
        "name": "Fair",
        "classifications": [
            {
                "primary": True,
                "segment": {"id": "KZFzniwnSyZfZ7v7n1", "name": "Miscellaneous"},
            }
        ],
    }
    assert map_ticketmaster_event(raw).category == "Other"


def test_unknown_segment_id_falls_back_to_segment_name():
    raw = {
        "id": "evt-family",
        "name": "Family Day",
        "classifications": [
            {
                "primary": True,
                "segment": {"id": "UNKNOWN_ID", "name": "Rodzina"},
            }
        ],
    }
    assert map_ticketmaster_event(raw).category == "Rodzina"
