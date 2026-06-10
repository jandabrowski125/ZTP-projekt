from datetime import UTC, datetime, timedelta

from user_app.db.models import SavedEventListType
from user_app.repositories.user_repository import UserRepository
from user_app.schemas.user_events import EventTargetRequest
from user_app.security import hash_password
from user_app.services import reminder_service


def _register(api_client, *, email: str, username: str) -> str:
    response = api_client.post(
        "/internal/v1/auth/register",
        json={
            "email": email,
            "password": "Secure1!",
            "username": username,
            "full_name": username.title(),
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _target(event_id: int = 42) -> dict:
    return {
        "public_event_id": event_id,
        "provider": "ticketmaster",
        "external_id": "TM_001",
        "event_snapshot": {
            "id": event_id,
            "title": "Sample Event",
            "short_title": "Sample",
            "month": "JUL",
            "day": "1",
            "time": "20:00",
            "day_label": "Tuesday, Jul 1",
            "venue": "Arena",
            "location": "Kraków",
            "distance": "2 km",
            "category": "Music",
            "category_color": "#7c3aed",
            "price": "Free",
            "image": "https://example.com/img.jpg",
            "tags": ["music"],
        },
    }


def test_favorite_enrolled_and_reminder_flow(api_client):
    token = _register(api_client, email="engage@example.com", username="engageuser")
    headers = {"Authorization": f"Bearer {token}"}
    target = _target()
    query = {
        "publicEventId": target["public_event_id"],
        "provider": target["provider"],
        "externalId": target["external_id"],
    }

    status = api_client.get("/internal/v1/users/me/event-actions", params=query, headers=headers)
    assert status.status_code == 200
    assert status.json() == {
        "favorited": False,
        "enrolled": False,
        "reminder_enabled": False,
    }

    assert api_client.put("/internal/v1/users/me/favorites", json=target, headers=headers).status_code == 204
    assert api_client.put("/internal/v1/users/me/enrolled", json=target, headers=headers).status_code == 204

    starts_at = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    reminder_payload = {**target, "enabled": True, "starts_at": starts_at}
    assert api_client.put("/internal/v1/users/me/reminders", json=reminder_payload, headers=headers).status_code == 204

    status = api_client.get("/internal/v1/users/me/event-actions", params=query, headers=headers)
    body = status.json()
    assert body["favorited"] is True
    assert body["enrolled"] is True
    assert body["reminder_enabled"] is True

    favorites = api_client.get("/internal/v1/users/me/favorites", headers=headers)
    assert favorites.status_code == 200
    assert len(favorites.json()) == 1

    enrolled = api_client.get("/internal/v1/users/me/enrolled", headers=headers)
    assert enrolled.status_code == 200
    assert len(enrolled.json()) == 1

    notifications = api_client.get("/internal/v1/users/me/notifications", headers=headers)
    assert notifications.status_code == 200
    notif_body = notifications.json()
    assert notif_body["unread_count"] == 0
    assert len(notif_body["items"]) == 0

    assert api_client.delete("/internal/v1/users/me/favorites", json=target, headers=headers).status_code == 204
    assert api_client.put(
        "/internal/v1/users/me/reminders",
        json={**target, "enabled": False},
        headers=headers,
    ).status_code == 204


def test_reminder_service_creates_active_subscription(db_session):
    repo = UserRepository(db_session)
    user = repo.create_user(
        email="remind@example.com",
        password_hash=hash_password("Secure1!"),
        username="reminduser",
        full_name="Remind User",
        bio=None,
        location=None,
        avatar_url=None,
        preferences={},
    )
    target = EventTargetRequest(
        public_event_id=7,
        provider="ticketmaster",
        external_id="TM_7",
        event_snapshot={"title": "Night Show"},
    )
    starts_at = datetime.now(UTC) + timedelta(days=2)
    reminder_service.enable_reminder(
        db_session,
        user.id,
        target,
        starts_at=starts_at,
        event_title="Night Show",
    )
    assert reminder_service.has_active_reminder(db_session, user.id, target)
    assert repo.has_saved_event(user.id, SavedEventListType.FAVORITE, target) is False
