"""Map custom event field changes to frontend notification change keys."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

EventChangeField = str


class _EventState(Protocol):
    title: str
    venue: str
    location: str
    address_line: str | None
    postal_code: str | None
    lat: float
    lng: float
    description: str | None
    price_label: str | None
    image_url: str | None
    category: str
    category_color: str
    tickets: list
    starts_at: datetime

def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _starts_at_change_fields(before: datetime, after: datetime) -> list[EventChangeField]:
    old = _as_utc(before)
    new = _as_utc(after)
    fields: list[EventChangeField] = []
    if old.date() != new.date():
        fields.append("date")
    if old.time() != new.time():
        fields.append("time")
    return fields


def _location_changed(before: _EventState, after: _EventState) -> bool:
    return (
        before.location != after.location
        or before.address_line != after.address_line
        or before.postal_code != after.postal_code
        or before.lat != after.lat
        or before.lng != after.lng
    )


def _starts_at_changed(before: datetime, after: datetime) -> bool:
    return _as_utc(before) != _as_utc(after)


def detect_custom_event_changes(
    before: _EventState,
    after: _EventState,
) -> list[EventChangeField]:
    """Return stable, de-duplicated change keys for a custom event update."""
    fields: list[EventChangeField] = []

    if before.title != after.title:
        fields.append("title")

    if _starts_at_changed(before.starts_at, after.starts_at):
        fields.extend(_starts_at_change_fields(before.starts_at, after.starts_at))

    if _location_changed(before, after):
        fields.append("location")

    if before.venue != after.venue:
        fields.append("venue")

    if before.description != after.description:
        fields.append("description")

    if before.price_label != after.price_label:
        fields.append("price")

    if before.image_url != after.image_url:
        fields.append("image")

    if before.category != after.category or before.category_color != after.category_color:
        fields.append("category")

    if before.tickets != after.tickets:
        fields.append("tickets")

    return list(dict.fromkeys(fields))
