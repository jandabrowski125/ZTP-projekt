from gateway.mappers.event_mapper import to_event_data_dto, to_map_pin_dto

_SAMPLE = {
    "id": 1,
    "title": "Electric Nights Techno Festival",
    "short_title": "Electric Nights",
    "month": "OCT",
    "day": "24",
    "time": "10:00 PM – 6:00 AM",
    "day_label": "Friday, Oct 24",
    "venue": "The Warehouse",
    "location": "Brooklyn, NY",
    "distance": "0.5 mi",
    "category": "Music",
    "category_color": "#7c3aed",
    "price": "$65",
    "image": "https://example.com/img.jpg",
    "tags": ["Techno"],
    "lat": 40.6975,
    "lng": -73.9742,
    "map_pin_category": "music",
    "featured": True,
    "event_date": "2025-10-24",
    "description": "Test",
    "lineup": [],
    "tickets": [],
}


def test_event_dto_uses_camel_case_aliases():
    dto = to_event_data_dto(_SAMPLE)
    dumped = dto.model_dump(by_alias=True)
    assert "shortTitle" in dumped
    assert "categoryColor" in dumped
    assert dumped["shortTitle"] == "Electric Nights"


def test_map_pin_uses_short_title_as_label():
    pin = to_map_pin_dto(_SAMPLE)
    assert pin.label == "Electric Nights"
    assert pin.category == "music"
