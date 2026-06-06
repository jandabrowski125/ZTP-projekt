import pytest

from user_app.db.models import SavedEventListType
from user_app.repositories.user_repository import UserAlreadyExistsError, UserRepository
from user_app.security import hash_password


def test_create_and_fetch_user(db_session):
    repo = UserRepository(db_session)
    user = repo.create_user(
        email="test@example.com",
        password_hash=hash_password("Secure1!"),
        username="testuser",
        full_name="Test User",
        bio="Hello",
        location="Kraków",
        avatar_url=None,
        preferences={"event_reminders": True},
    )
    assert user.id is not None
    fetched = repo.get_by_email("test@example.com")
    assert fetched is not None
    assert fetched.username == "testuser"


def test_duplicate_email_raises(db_session):
    repo = UserRepository(db_session)
    repo.create_user(
        email="dup@example.com",
        password_hash=hash_password("Secure1!"),
        username="userone",
        full_name="One",
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )
    with pytest.raises(UserAlreadyExistsError):
        repo.create_user(
            email="dup@example.com",
            password_hash=hash_password("Secure1!"),
            username="usertwo",
            full_name="Two",
            bio=None,
            location=None,
            avatar_url=None,
            preferences={},
        )


def test_favorites_and_past_events(db_session):
    repo = UserRepository(db_session)
    user = repo.create_user(
        email="fav@example.com",
        password_hash=hash_password("Secure1!"),
        username="favuser",
        full_name="Fav",
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )
    fav = repo.add_saved_aggregated_event(
        user_id=user.id,
        list_type=SavedEventListType.FAVORITE,
        public_event_id=101,
        provider="ticketmaster",
        external_id="abc",
        event_snapshot={"title": "Concert"},
        attended_at=None,
    )
    past = repo.add_saved_aggregated_event(
        user_id=user.id,
        list_type=SavedEventListType.PAST,
        public_event_id=102,
        provider="ticketmaster",
        external_id="xyz",
        event_snapshot=None,
        attended_at=None,
    )
    assert len(repo.list_saved_events(user.id, SavedEventListType.FAVORITE)) == 1
    assert len(repo.list_saved_events(user.id, SavedEventListType.PAST)) == 1
    assert repo.remove_saved_event(user.id, fav.id)
    assert len(repo.list_saved_events(user.id, SavedEventListType.FAVORITE)) == 0
    assert past.id is not None
