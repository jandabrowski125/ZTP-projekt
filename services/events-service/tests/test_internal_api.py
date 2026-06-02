from fastapi.testclient import TestClient

from events_app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_events():
    response = client.get("/internal/v1/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["short_title"]


def test_get_event():
    response = client.get("/internal/v1/events/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_get_event_not_found():
    response = client.get("/internal/v1/events/99999")
    assert response.status_code == 404


def test_list_categories():
    response = client.get("/internal/v1/categories")
    assert response.status_code == 200
    labels = [c["label"] for c in response.json()]
    assert "Music" in labels
    assert "All Events" in labels
