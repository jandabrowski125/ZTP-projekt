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


def _create_event_payload(**overrides):
    payload = {
        "title": "Community Jam",
        "short_title": "Jam",
        "description": "Open session",
        "venue": "Studio",
        "location": "Kraków",
        "lat": 50.05,
        "lng": 19.94,
        "category": "Music",
        "category_color": "#7c3aed",
        "price_label": "Free",
        "image_url": None,
        "tags": ["music"],
        "starts_at": "2026-07-01T20:00:00+00:00",
        "ends_at": None,
        "lineup": [],
        "tickets": [],
        "publish": True,
    }
    payload.update(overrides)
    return payload


def test_custom_event_persists_address_fields(api_client):
    token = _register(api_client, email="addr@example.com", username="addruser")
    create = api_client.post(
        "/internal/v1/custom-events",
        headers={"Authorization": f"Bearer {token}"},
        json=_create_event_payload(
            address_line="ul. Dolnych Młynów 10",
            postal_code="31-001",
        ),
    )
    assert create.status_code == 201
    body = create.json()
    assert body["address_line"] == "ul. Dolnych Młynów 10"
    assert body["postal_code"] == "31-001"

    event_id = body["id"]
    listed = api_client.get(
        "/internal/v1/custom-events/published",
    )
    assert listed.status_code == 200
    published = next(item for item in listed.json() if item["id"] == event_id)
    assert published["address_line"] == "ul. Dolnych Młynów 10"
    assert published["postal_code"] == "31-001"


def test_custom_event_update_and_delete_owner_only(api_client):
    owner_token = _register(api_client, email="owner2@example.com", username="owner2")
    other_token = _register(api_client, email="intruder@example.com", username="intruder")

    create = api_client.post(
        "/internal/v1/custom-events",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=_create_event_payload(),
    )
    assert create.status_code == 201
    event_id = create.json()["id"]

    denied_update = api_client.patch(
        f"/internal/v1/custom-events/{event_id}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"title": "Stolen"},
    )
    assert denied_update.status_code == 404

    allowed_update = api_client.patch(
        f"/internal/v1/custom-events/{event_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Updated Jam"},
    )
    assert allowed_update.status_code == 200
    assert allowed_update.json()["title"] == "Updated Jam"

    denied_delete = api_client.delete(
        f"/internal/v1/custom-events/{event_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied_delete.status_code == 404

    allowed_delete = api_client.delete(
        f"/internal/v1/custom-events/{event_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert allowed_delete.status_code == 204

    missing = api_client.patch(
        f"/internal/v1/custom-events/{event_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Gone"},
    )
    assert missing.status_code == 404
