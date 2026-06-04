def test_register_rejects_weak_password(api_client):
    response = api_client.post(
        "/internal/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "password",
            "username": "weakuser",
            "full_name": "Weak User",
        },
    )
    assert response.status_code == 422


def test_register_rejects_duplicate_email(api_client):
    payload = {
        "email": "dup@example.com",
        "password": "Secure1!",
        "username": "userone",
        "full_name": "One",
    }
    assert api_client.post("/internal/v1/auth/register", json=payload).status_code == 201
    response = api_client.post(
        "/internal/v1/auth/register",
        json={**payload, "username": "usertwo", "full_name": "Two"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"
