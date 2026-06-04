import pytest

from user_app.validation import validate_strong_password


def test_validate_strong_password_accepts_valid():
    assert validate_strong_password("Abcdef1!") == "Abcdef1!"


@pytest.mark.parametrize(
    "password",
    [
        "short1!",
        "Abcdefgh!",
        "Abcdefg1",
    ],
)
def test_validate_strong_password_rejects_weak(password: str):
    with pytest.raises(ValueError):
        validate_strong_password(password)
