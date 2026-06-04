from user_app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("secure-password-1")
    assert verify_password("secure-password-1", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token = create_access_token("550e8400-e29b-41d4-a716-446655440000")
    assert decode_access_token(token) == "550e8400-e29b-41d4-a716-446655440000"
    assert decode_access_token("invalid") is None
