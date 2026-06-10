import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from eventradar_common.event_ids import public_id_for

from user_app.db.models import NotificationType, SavedEventListType, UserNotification
from user_app.repositories.custom_event_repository import CustomEventRepository
from user_app.repositories.user_repository import UserRepository
from user_app.schemas.user_events import EventTargetRequest
from user_app.security import hash_password


def _create_custom_event(repo: CustomEventRepository, owner_id: uuid.UUID) -> uuid.UUID:
    event = repo.create(
        owner_user_id=owner_id,
        title="Neon Nights Festival",
        short_title="Neon",
        description="Outdoor show",
        venue="Arena",
        location="Kraków",
        address_line=None,
        postal_code=None,
        lat=50.06,
        lng=19.94,
        category="Music",
        category_color="#7c3aed",
        price_label="Free",
        image_url=None,
        tags=[],
        starts_at=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        ends_at=None,
        lineup=[],
        tickets=[],
        publish=True,
    )
    return event.id


def test_update_custom_event_notifies_tracking_users(db_session):
    user_repo = UserRepository(db_session)
    owner = user_repo.create_user(
        email="owner@example.com",
        password_hash=hash_password("Secure1!"),
        username="owneruser",
        full_name="Owner",
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )
    fan = user_repo.create_user(
        email="fan@example.com",
        password_hash=hash_password("Secure1!"),
        username="fanuser",
        full_name="Fan",
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )

    custom_repo = CustomEventRepository(db_session)
    event_id = _create_custom_event(custom_repo, owner.id)
    external_id = str(event_id)
    public_event_id = public_id_for("custom", external_id)

    target = EventTargetRequest(
        public_event_id=public_event_id,
        provider="custom",
        external_id=external_id,
        custom_event_id=event_id,
    )
    user_repo.add_saved_event(
        user_id=fan.id,
        list_type=SavedEventListType.FAVORITE,
        target=target,
    )

    updated = custom_repo.update(
        event_id,
        owner_user_id=owner.id,
        starts_at=datetime(2026, 8, 1, 20, 0, tzinfo=UTC),
        venue="New Arena",
    )
    assert updated is not None

    fan_notifications = list(
        db_session.scalars(
            select(UserNotification).where(UserNotification.user_id == fan.id)
        ).all()
    )
    assert len(fan_notifications) == 1
    notification = fan_notifications[0]
    assert notification.type == NotificationType.EVENT_UPDATED
    assert notification.event_title == "Neon Nights Festival"
    assert notification.public_event_id == public_event_id
    assert notification.community_event_id == event_id
    assert set(notification.changed_fields) == {"time", "venue"}

def test_update_custom_event_notifies_owner_when_tracking_own_event(db_session):
    user_repo = UserRepository(db_session)
    owner = user_repo.create_user(
        email="selftrack@example.com",
        password_hash=hash_password("Secure1!"),
        username="selftrack",
        full_name="Owner",
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )

    custom_repo = CustomEventRepository(db_session)
    event_id = _create_custom_event(custom_repo, owner.id)
    external_id = str(event_id)
    public_event_id = public_id_for("custom", external_id)

    user_repo.add_saved_event(
        user_id=owner.id,
        list_type=SavedEventListType.FAVORITE,
        target=EventTargetRequest(
            public_event_id=public_event_id,
            provider="custom",
            external_id=external_id,
            custom_event_id=event_id,
        ),
    )

    assert custom_repo.update(
        event_id,
        owner_user_id=owner.id,
        venue="Updated Arena",
    )

    owner_notifications = list(
        db_session.scalars(
            select(UserNotification).where(UserNotification.user_id == owner.id)
        ).all()
    )
    assert len(owner_notifications) == 1
    assert owner_notifications[0].type == NotificationType.EVENT_UPDATED
