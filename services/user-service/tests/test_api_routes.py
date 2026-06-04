def test_register_and_login(api_client):
    register = api_client.post(
        "/internal/v1/auth/register",
        json={
            "email": "api@example.com",
            "password": "Secure1!",
            "username": "apiuser",
            "full_name": "API User",
        },
    )
    assert register.status_code == 201
    token = register.json()["access_token"]

    login = api_client.post(
        "/internal/v1/auth/login",
        json={"email": "api@example.com", "password": "Secure1!"},
    )
    assert login.status_code == 200

    me = api_client.get(
        "/internal/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "apiuser"
