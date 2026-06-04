from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from events_app.api.date_validation import validate_date_range


def test_rejects_date_from_before_today():
    yesterday = date.today() - timedelta(days=1)
    with pytest.raises(HTTPException) as exc:
        validate_date_range(yesterday, date.today())
    assert exc.value.status_code == 400
    assert "date_from cannot be before today" in exc.value.detail


def test_rejects_date_to_before_today():
    yesterday = date.today() - timedelta(days=1)
    with pytest.raises(HTTPException) as exc:
        validate_date_range(date.today(), yesterday)
    assert exc.value.status_code == 400
    assert "date_to cannot be before today" in exc.value.detail


def test_rejects_inverted_range():
    future = date.today() + timedelta(days=10)
    sooner = date.today() + timedelta(days=2)
    with pytest.raises(HTTPException) as exc:
        validate_date_range(future, sooner)
    assert exc.value.status_code == 400


def test_accepts_same_day_range():
    today = date.today()
    validate_date_range(today, today)


def test_accepts_valid_future_range():
    start = date.today() + timedelta(days=1)
    end = date.today() + timedelta(days=7)
    validate_date_range(start, end)
