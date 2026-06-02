from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from gateway.api.routes import get_facade
from gateway.dto.events import (
    CategoryDTO,
    EventDataDTO,
    EventDetailsDTO,
    EventsListResponseDTO,
    MapPinDTO,
)
from gateway.main import app
from gateway.services.event_facade import EventFacade


@pytest.fixture
def mock_facade() -> EventFacade:
    facade = AsyncMock(spec=EventFacade)
    facade.list_events.return_value = EventsListResponseDTO(
        items=[
            EventDataDTO(
                id=1,
                shortTitle="Electric Nights",
                title="Electric Nights Techno Festival",
                month="OCT",
                day="24",
                time="10:00 PM",
                dayLabel="Friday, Oct 24",
                venue="The Warehouse",
                location="Brooklyn, NY",
                distance="0.5 mi",
                category="Music",
                categoryColor="#7c3aed",
                price="$65",
                image="https://example.com/img.jpg",
                tags=["Techno"],
            )
        ],
        total=1,
    )
    facade.get_event.return_value = EventDetailsDTO(
        id=1,
        shortTitle="Electric Nights",
        title="Electric Nights Techno Festival",
        month="OCT",
        day="24",
        time="10:00 PM",
        dayLabel="Friday, Oct 24",
        venue="The Warehouse",
        location="Brooklyn, NY",
        distance="0.5 mi",
        category="Music",
        categoryColor="#7c3aed",
        price="$65",
        image="https://example.com/img.jpg",
        tags=["Techno"],
        description="About",
        lineup=[],
        tickets=[],
    )
    facade.list_map_pins.return_value = [
        MapPinDTO(
            id=1,
            lat=40.6975,
            lng=-73.9742,
            label="Electric Nights",
            time="10:00 PM",
            price="$65",
            category="music",
            featured=True,
        )
    ]
    facade.list_categories.return_value = [
        CategoryDTO(label="Music", icon="music_note"),
    ]
    return facade


@pytest.fixture
def client(mock_facade: EventFacade):
    app.dependency_overrides[get_facade] = lambda: mock_facade
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200


def test_list_events_returns_camel_case(client: TestClient):
    response = client.get("/api/v1/events")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["shortTitle"] == "Electric Nights"


def test_get_event(client: TestClient):
    response = client.get("/api/v1/events/1")
    assert response.status_code == 200
    assert response.json()["description"] == "About"


def test_map_pins(client: TestClient):
    response = client.get("/api/v1/map/pins")
    assert response.status_code == 200
    assert response.json()[0]["category"] == "music"


def test_categories(client: TestClient):
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert response.json()[0]["label"] == "Music"
