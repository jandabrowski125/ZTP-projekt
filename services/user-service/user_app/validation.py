import re

PASSWORD_MIN_LENGTH = 8
_SPECIAL_CHAR_PATTERN = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;/'`~]")


def validate_strong_password(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        msg = f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
        raise ValueError(msg)
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not _SPECIAL_CHAR_PATTERN.search(password):
        raise ValueError("Password must contain at least one special character")
    return password
