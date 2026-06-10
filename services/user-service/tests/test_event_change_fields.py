from datetime import UTC, datetime

from user_app.services.custom_event_notifications import CustomEventSnapshot
from user_app.services.event_change_fields import detect_custom_event_changes


class _EventStub:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _base_event(**overrides):
    defaults = {
        "title": "Open Mic",
        "venue": "Club X",
        "location": "Kraków",
        "address_line": None,
        "postal_code": None,
        "lat": 50.05,
        "lng": 19.94,
        "description": "Weekly session",
        "price_label": "Free",
        "image_url": None,
        "category": "Music",
        "category_color": "#7c3aed",
        "tickets": [],
        "starts_at": datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return _EventStub(**defaults)


def test_detect_time_change_only():
    before = _base_event()
    after = _base_event(starts_at=datetime(2026, 6, 15, 21, 0, tzinfo=UTC))
    assert detect_custom_event_changes(before, after) == ["time"]


def test_detect_date_and_time_change():
    before = _base_event()
    after = _base_event(starts_at=datetime(2026, 6, 16, 21, 0, tzinfo=UTC))
    assert detect_custom_event_changes(before, after) == ["date", "time"]


def test_detect_location_change_from_coordinates():
    before = _base_event()
    after = _base_event(lat=50.06, lng=19.95)
    assert detect_custom_event_changes(before, after) == ["location"]


def test_detect_multiple_field_changes():
    before = _base_event()
    after = _base_event(venue="New Club", price_label="10 PLN")
    assert detect_custom_event_changes(before, after) == ["venue", "price"]


def test_snapshot_preserves_state_for_change_detection():
    before = CustomEventSnapshot(
        title="Open Mic",
        venue="Club X",
        location="Kraków",
        address_line=None,
        postal_code=None,
        lat=50.05,
        lng=19.94,
        description="Weekly session",
        price_label="Free",
        image_url=None,
        category="Music",
        category_color="#7c3aed",
        tickets=[],
        starts_at=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
    )
    after = _base_event(starts_at=datetime(2026, 6, 15, 21, 0, tzinfo=UTC))
    assert detect_custom_event_changes(before, after) == ["time"]
