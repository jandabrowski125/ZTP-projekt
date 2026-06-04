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
    mine = events.list_for_owner(owner.id)
    assert len(mine) == 1
    published = events.list_published()
    assert any(row.id == event.id for row in published)
