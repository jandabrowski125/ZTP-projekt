from eventradar_common.event_ids import public_id_for

from test_custom_event_api import _create_event_payload, _register


def test_custom_event_update_notifies_tracking_user(api_client):
    owner_token = _register(api_client, email="owner-upd@example.com", username="ownerupd")
    fan_token = _register(api_client, email="fan-upd@example.com", username="fanupd")

    create = api_client.post(
        "/internal/v1/custom-events",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=_create_event_payload(title="Sunset Sessions"),
    )
    assert create.status_code == 201
    event_id = create.json()["id"]
    public_event_id = public_id_for("custom", event_id)

    favorite = api_client.put(
        "/internal/v1/users/me/favorites",
        headers={"Authorization": f"Bearer {fan_token}"},
        json={
            "public_event_id": public_event_id,
            "provider": "custom",
            "external_id": event_id,
            "custom_event_id": event_id,
        },
    )
    assert favorite.status_code == 204

    update = api_client.patch(
        f"/internal/v1/custom-events/{event_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "starts_at": "2026-07-02T20:00:00+00:00",
            "location": "Gdańsk",
            "venue": "Harbour Hall",
            "lat": 54.35,
            "lng": 18.65,
        },
    )
    assert update.status_code == 200

    notifications = api_client.get(
        "/internal/v1/users/me/notifications",
        headers={"Authorization": f"Bearer {fan_token}"},
    )
    assert notifications.status_code == 200
    body = notifications.json()
    assert body["unread_count"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["type"] == "event_updated"
    assert item["event_title"] == "Sunset Sessions"
    assert "date" in item["changed_fields"]
    assert "location" in item["changed_fields"]
