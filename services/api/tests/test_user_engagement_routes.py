"""Tests for gateway user engagement routes (favorites, enrolled, reminders, notifications)."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import HTTPStatusError, Request, Response

from gateway.api.user_routes import get_events_client, get_user_client
from gateway.clients.events_client import EventsServiceClient
from gateway.clients.user_client import UserServiceClient
from gateway.main import app

_AUTH = "Bearer test-token"
_EVENT_ID = 42

_EVENT_RAW = {
    "id": _EVENT_ID,
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
    "provider": "ticketmaster",
    "external_id": "TM_001",
}

_SAVED_RAW = {
    "id": str(uuid4()),
    "list_type": "favorite",
    "public_event_id": _EVENT_ID,
    "provider": "ticketmaster",
    "external_id": "TM_001",
    "custom_event_id": None,
    "event_snapshot": _EVENT_RAW,
    "attended_at": None,
}


@pytest.fixture
def mock_user_client() -> UserServiceClient:
    client = AsyncMock(spec=UserServiceClient)
    client.list_favorites.return_value = [_SAVED_RAW]
    client.list_enrolled.return_value = [_SAVED_RAW]
    client.get_event_action_status.return_value = {
        "favorited": True,
        "enrolled": False,
        "reminder_enabled": True,
    }
    client.list_notifications.return_value = {
        "items": [
            {
                "id": str(uuid4()),
                "type": "event_reminder",
                "title": "Event starts in 1 hour",
                "body": "Sample Event",
                "public_event_id": _EVENT_ID,
                "community_event_id": None,
                "scheduled_for": "2026-07-01T19:00:00+00:00",
                "read": False,
                "created_at": "2026-07-01T18:00:00+00:00",
            }
        ],
        "unread_count": 1,
    }
    client.upsert_favorite.return_value = None
    client.remove_favorite_by_ref.return_value = None
    client.upsert_enrolled.return_value = None
    client.remove_enrolled_by_ref.return_value = None
    client.set_event_reminder.return_value = None
    client.mark_notification_read.return_value = None
    client.mark_all_notifications_read.return_value = None
    client.clear_all_notifications.return_value = None
    client.list_past_events.return_value = [{"id": "past-1"}, {"id": "past-2"}]
    client.list_enrolled.return_value = [
        {
            "id": str(uuid4()),
            "list_type": "enrolled",
            "public_event_id": _EVENT_ID,
            "provider": "ticketmaster",
            "external_id": "TM_001",
            "custom_event_id": None,
            "event_snapshot": None,
            "attended_at": None,
        }
    ]
    return client


@pytest.fixture
def mock_events_client() -> EventsServiceClient:
    client = AsyncMock(spec=EventsServiceClient)
    client.get_event.return_value = _EVENT_RAW
    return client


@pytest.fixture
def client(mock_user_client: UserServiceClient, mock_events_client: EventsServiceClient):
    app.dependency_overrides[get_user_client] = lambda: mock_user_client
    app.dependency_overrides[get_events_client] = lambda: mock_events_client
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_favorites_returns_event_items(
    client: TestClient,
    mock_events_client: EventsServiceClient,
):
    mock_events_client.get_event.return_value = _EVENT_RAW
    response = client.get("/api/v1/users/me/favorites", headers={"Authorization": _AUTH})
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert body["items"][0]["id"] == _EVENT_ID
    assert body["items"][0]["title"] == "Sample Event"


def test_get_event_action_status_returns_camel_case(client: TestClient):
    response = client.get(
        f"/api/v1/users/me/event-actions?eventId={_EVENT_ID}",
        headers={"Authorization": _AUTH},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["favorited"] is True
    assert body["reminderEnabled"] is True


def test_put_favorite_returns_204(client: TestClient, mock_user_client: UserServiceClient):
    response = client.put(
        "/api/v1/users/me/favorites",
        json={"eventId": _EVENT_ID},
        headers={"Authorization": _AUTH},
    )
    assert response.status_code == 204
    mock_user_client.upsert_favorite.assert_awaited_once()


def test_list_notifications_returns_camel_case(client: TestClient, mock_user_client: UserServiceClient):
    notification_id = str(uuid4())
    mock_user_client.list_notifications.return_value = {
        "items": [
            {
                "id": notification_id,
                "type": "event_updated",
                "title": "Event updated",
                "body": "Event details have been updated.",
                "public_event_id": _EVENT_ID,
                "community_event_id": None,
                "event_title": "Sample Event",
                "changed_fields": ["time", "venue"],
                "scheduled_for": "2026-07-01T19:00:00+00:00",
                "read": False,
                "created_at": "2026-07-01T18:00:00+00:00",
            }
        ],
        "unread_count": 1,
    }
    response = client.get("/api/v1/users/me/notifications", headers={"Authorization": _AUTH})
    assert response.status_code == 200
    body = response.json()
    assert body["unreadCount"] == 1
    item = body["items"][0]
    assert item["eventId"] == _EVENT_ID
    assert item["eventTitle"] == "Sample Event"
    assert item["changedFields"] == ["time", "venue"]


def test_profile_stats_returns_counts(
    client: TestClient,
    mock_events_client: EventsServiceClient,
):
    from datetime import UTC, datetime, timedelta

    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    mock_events_client.get_event.return_value = {**_EVENT_RAW, "starts_at": future}
    response = client.get("/api/v1/users/me/profile-stats", headers={"Authorization": _AUTH})
    assert response.status_code == 200
    body = response.json()
    assert body["eventsAttended"] == 2
    assert body["upcoming"] == 1


def test_clear_notifications_returns_204(
    client: TestClient,
    mock_user_client: UserServiceClient,
):
    response = client.delete(
        "/api/v1/users/me/notifications",
        headers={"Authorization": _AUTH},
    )
    assert response.status_code == 204
    mock_user_client.clear_all_notifications.assert_awaited_once()


def test_engagement_routes_require_auth(client: TestClient):
    assert client.get("/api/v1/users/me/enrolled").status_code == 401
    assert client.get("/api/v1/users/me/notifications").status_code == 401
    assert client.get("/api/v1/users/me/profile-stats").status_code == 401
    assert client.delete("/api/v1/users/me/notifications").status_code == 401
    assert client.get(f"/api/v1/users/me/event-actions?eventId={_EVENT_ID}").status_code == 401
