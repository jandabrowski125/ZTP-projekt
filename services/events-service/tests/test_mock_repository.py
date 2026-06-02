from datetime import date

from events_app.repositories.mock_repository import MockEventRepository


def test_list_all_events():
    repo = MockEventRepository()
    events = repo.list_events()
    assert len(events) >= 5


def test_filter_by_category():
    repo = MockEventRepository()
    music = repo.list_events(category="Music")
    assert all(e.category == "Music" for e in music)
    assert len(music) >= 2


def test_filter_all_events_category_returns_everything():
    repo = MockEventRepository()
    all_events = repo.list_events(category="All Events")
    assert len(all_events) == len(repo.list_events())


def test_filter_by_location():
    repo = MockEventRepository()
    brooklyn = repo.list_events(location="Brooklyn")
    assert len(brooklyn) >= 3
    assert all("Brooklyn" in e.location for e in brooklyn)


def test_filter_by_query():
    repo = MockEventRepository()
    results = repo.list_events(query="techno")
    assert len(results) >= 1
    assert any("techno" in e.title.lower() for e in results)


def test_get_event_by_id():
    repo = MockEventRepository()
    event = repo.get_event(1)
    assert event is not None
    assert event.title == "Electric Nights Techno Festival"


def test_get_missing_event_returns_none():
    repo = MockEventRepository()
    assert repo.get_event(9999) is None


def test_date_range_filter():
    repo = MockEventRepository()
    results = repo.list_events(
        date_from=date(2025, 10, 24),
        date_to=date(2025, 10, 26),
    )
    assert all(date(2025, 10, 24) <= e.event_date <= date(2025, 10, 26) for e in results)
