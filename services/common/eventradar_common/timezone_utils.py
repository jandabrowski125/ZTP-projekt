"""Timezone helpers for event scheduling and display."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

_tf = None


def _timezone_finder():
    global _tf
    if _tf is None:
        from timezonefinder import TimezoneFinder

        _tf = TimezoneFinder()
    return _tf


@lru_cache(maxsize=512)
def timezone_at(lat: float, lng: float) -> str:
    """Resolve an IANA timezone name for geographic coordinates."""
    tz_name = _timezone_finder().timezone_at(lat=round(lat, 4), lng=round(lng, 4))
    return tz_name or "UTC"


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_timezone(dt: datetime, tz_name: str) -> datetime:
    return ensure_utc(dt).astimezone(ZoneInfo(tz_name))


def format_time_12h(dt: datetime) -> str:
    """Cross-platform 12-hour time without a leading zero on the hour."""
    hour = int(dt.strftime("%I"))
    minute = dt.strftime("%M")
    ampm = dt.strftime("%p")
    return f"{hour}:{minute} {ampm}"
