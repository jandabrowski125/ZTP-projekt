"""Tests for gateway user routes: favorites and past-events endpoints."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import HTTPStatusError, Request, Response

from gateway.api.user_routes import get_events_client, get_user_client
from gateway.clients.events_client import EventsServiceClient
from gateway.clients.user_client import UserServiceClient
from gateway.main import app

_SAVED_ID = uuid4()
_SAVED_RAW = {
    "id": str(_SAVED_ID),
    "list_type": "favorite",
    "public_event_id": 42,
    "provider": "ticketmaster",
    "external_id": "TM_001",
    "custom_event_id": None,
    "event_snapshot": None,
    "attended_at": None,
}

_PAST_RAW = {
    "id": str(uuid4()),
    "list_type": "past",
    "public_event_id": 99,
    "provider": "ticketmaster",
    "external_id": "TM_002",
    "custom_event_id": None,
    "event_snapshot": None,
    "attended_at": "2026-01-15",
}

_AUTH = "Bearer test-token"


@pytest.fixture
def mock_user_client() -> UserServiceClient:
    client = AsyncMock(spec=UserServiceClient)
    client.list_favorites.return_value = [
        {
            **_SAVED_RAW,
            "event_snapshot": {
                "id": 42,
                "title": "Sample",
                "short_title": "Sample",
                "month": "JUL",
                "day": "1",
                "time": "20:00",
                "day_label": "Tue",
                "venue": "Arena",
                "location": "Kraków",
                "distance": "2 km",
                "category": "Music",
                "category_color": "#7c3aed",
                "price": "Free",
                "image": "https://example.com/img.jpg",
                "tags": [],
            },
        }
    ]
    client.add_favorite.return_value = _SAVED_RAW
    client.remove_favorite.return_value = None
    client.list_past_events.return_value = [_PAST_RAW]
    client.add_past_event.return_value = _PAST_RAW
    return client


@pytest.fixture
def mock_events_client() -> EventsServiceClient:
    client = AsyncMock(spec=EventsServiceClient)
    client.get_event.return_value = {
        "id": 42,
        "title": "Sample",
        "short_title": "Sample",
        "month": "JUL",
        "day": "1",
        "time": "20:00",
        "day_label": "Tue",
        "venue": "Arena",
        "location": "Kraków",
        "distance": "2 km",
        "category": "Music",
        "category_color": "#7c3aed",
        "price": "Free",
        "image": "https://example.com/img.jpg",
        "tags": [],
    }
    return client


@pytest.fixture
def client(mock_user_client: UserServiceClient, mock_events_client: EventsServiceClient):
    app.dependency_overrides[get_user_client] = lambda: mock_user_client
    app.dependency_overrides[get_events_client] = lambda: mock_events_client
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_favorites_returns_camel_case(client: TestClient):
    response = client.get("/api/v1/users/me/favorites", headers={"Authorization": _AUTH})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body["items"][0]["id"] == 42


def test_list_favorites_requires_auth(client: TestClient):
    response = client.get("/api/v1/users/me/favorites")
    assert response.status_code == 401


def test_add_favorite_returns_201(client: TestClient):
    payload = {
        "publicEventId": 42,
        "provider": "ticketmaster",
        "externalId": "TM_001",
    }
    response = client.post("/api/v1/users/me/favorites", json=payload, headers={"Authorization": _AUTH})
    assert response.status_code == 201
    body = response.json()
    assert body["listType"] == "favorite"
    assert body["publicEventId"] == 42


def test_add_favorite_requires_auth(client: TestClient):
    payload = {"publicEventId": 42, "provider": "ticketmaster", "externalId": "TM_001"}
    response = client.post("/api/v1/users/me/favorites", json=payload)
    assert response.status_code == 401


def test_remove_favorite_returns_204(client: TestClient):
    response = client.delete(
        f"/api/v1/users/me/favorites/{_SAVED_ID}",
        headers={"Authorization": _AUTH},
    )
    assert response.status_code == 204


def test_remove_favorite_requires_auth(client: TestClient):
    response = client.delete(f"/api/v1/users/me/favorites/{_SAVED_ID}")
    assert response.status_code == 401


def test_remove_favorite_proxies_404(client: TestClient, mock_user_client: UserServiceClient):
    mock_req = Request("DELETE", "http://user-service/internal/v1/users/me/favorites/x")
    mock_resp = Response(404, request=mock_req)
    mock_user_client.remove_favorite.side_effect = HTTPStatusError("not found", request=mock_req, response=mock_resp)

    response = client.delete(
        f"/api/v1/users/me/favorites/{_SAVED_ID}",
        headers={"Authorization": _AUTH},
    )
    assert response.status_code == 404


def test_list_past_events_returns_camel_case(client: TestClient):
    response = client.get("/api/v1/users/me/past-events", headers={"Authorization": _AUTH})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["listType"] == "past"
    assert body[0]["attendedAt"] == "2026-01-15"


def test_list_past_events_requires_auth(client: TestClient):
    response = client.get("/api/v1/users/me/past-events")
    assert response.status_code == 401


def test_add_past_event_returns_201(client: TestClient):
    payload = {
        "publicEventId": 99,
        "provider": "ticketmaster",
        "externalId": "TM_002",
        "attendedAt": "2026-01-15",
    }
    response = client.post(
        "/api/v1/users/me/past-events",
        json=payload,
        headers={"Authorization": _AUTH},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["listType"] == "past"
    assert body["attendedAt"] == "2026-01-15"


def test_add_past_event_requires_auth(client: TestClient):
    payload = {"publicEventId": 99, "provider": "ticketmaster", "externalId": "TM_002"}
    response = client.post("/api/v1/users/me/past-events", json=payload)
    assert response.status_code == 401
