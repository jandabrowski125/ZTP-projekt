from datetime import UTC, datetime

from user_app.repositories.custom_event_repository import CustomEventRepository
from user_app.repositories.user_repository import UserRepository
from user_app.security import hash_password


def test_create_custom_event(db_session):
    users = UserRepository(db_session)
    owner = users.create_user(
        email="venue@example.com",
        password_hash=hash_password("Secure1!"),
        username="venue",
        full_name="Venue Owner",
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )
    events = CustomEventRepository(db_session)
    event = events.create(
        owner_user_id=owner.id,
        title="Open Mic Night",
        short_title="Open Mic",
        description="Weekly session",
        venue="Club X",
        location="Kraków",
        address_line="ul. Floriańska 1",
        postal_code="31-019",
        lat=50.05,
        lng=19.94,
        category="Music",
        category_color="#7c3aed",
        price_label="Free",
        image_url=None,
        tags=["music"],
        starts_at=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
        ends_at=None,
        lineup=[],
        tickets=[],
        publish=True,
    )
    assert event.status.value == "published"
    assert event.address_line == "ul. Floriańska 1"
    assert event.postal_code == "31-019"
    mine = events.list_for_owner(owner.id)
    assert len(mine) == 1
    published = events.list_published()
    assert any(row.id == event.id for row in published)


def _create_event_for_owner(db_session, *, email: str, username: str):
    users = UserRepository(db_session)
    owner = users.create_user(
        email=email,
        password_hash=hash_password("Secure1!"),
        username=username,
        full_name=username.title(),
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )
    events = CustomEventRepository(db_session)
    event = events.create(
        owner_user_id=owner.id,
        title=f"{username} Event",
        short_title="Event",
        description="Desc",
        venue="Club",
        location="Kraków",
        address_line=None,
        postal_code=None,
        lat=50.05,
        lng=19.94,
        category="Music",
        category_color="#7c3aed",
        price_label="Free",
        image_url=None,
        tags=[],
        starts_at=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
        ends_at=None,
        lineup=[],
        tickets=[],
        publish=True,
    )
    return owner, event


def test_update_custom_event_owner_only(db_session):
    owner, event = _create_event_for_owner(db_session, email="owner@example.com", username="owner")
    other, _ = _create_event_for_owner(db_session, email="other@example.com", username="other")
    repo = CustomEventRepository(db_session)

    updated = repo.update(event.id, owner_user_id=owner.id, title="Updated Title")
    assert updated is not None
    assert updated.title == "Updated Title"

    denied = repo.update(event.id, owner_user_id=other.id, title="Hacked")
    assert denied is None


def test_delete_custom_event_owner_only(db_session):
    owner, event = _create_event_for_owner(db_session, email="del@example.com", username="deleter")
    other, _ = _create_event_for_owner(db_session, email="nodel@example.com", username="nodel")
    repo = CustomEventRepository(db_session)

    assert repo.delete(event.id, owner_user_id=other.id) is False
    assert repo.get(event.id) is not None

    assert repo.delete(event.id, owner_user_id=owner.id) is True
    assert repo.get(event.id) is None
