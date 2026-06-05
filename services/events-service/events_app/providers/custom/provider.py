import logging
from datetime import datetime, timezone
from typing import Any

from events_app.domain.models import Event, LineupArtist, MapPinCategory, Ticket
from events_app.providers.custom.client import UserServiceCustomClient
from events_app.providers.id_registry import EventIdRegistry, public_id_for
from events_app.providers.protocol import ProviderSearchParams

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_time(dt: datetime) -> str:
    """Cross-platform 12-hour time without leading zero."""
    hour = int(dt.strftime("%I"))
    minute = dt.strftime("%M")
    ampm = dt.strftime("%p")
    return f"{hour}:{minute} {ampm}"


class CustomEventProvider:
    name = "custom"

    def __init__(self, client: UserServiceCustomClient, registry: EventIdRegistry) -> None:
        self._client = client
        self._registry = registry

    def _map_to_event(self, raw: dict[str, Any]) -> Event:
        external_id = raw.get("id")
        public_id = public_id_for(self.name, str(external_id))
        self._registry.register(self.name, str(external_id), public_id)

        starts_at = raw.get("starts_at")
        if isinstance(starts_at, str):
            try:
                starts_dt = datetime.fromisoformat(starts_at)
            except ValueError:
                starts_dt = _now_utc()
        elif isinstance(starts_at, datetime):
            starts_dt = starts_at
        else:
            starts_dt = _now_utc()

        title = raw.get("title") or raw.get("short_title") or "Untitled"
        short_title = raw.get("short_title") or title[:80]
        month = starts_dt.strftime("%b").upper()
        day = starts_dt.strftime("%d").lstrip("0") or "1"
        time_str = _format_time(starts_dt)
        day_label = starts_dt.strftime("%A, %b %d")

        tags = tuple(raw.get("tags") or [])
        lineup = tuple(
            LineupArtist(
                name=item.get("name") or "",
                role=item.get("role") or "",
                role_color=item.get("role_color") or "#000000",
                time=item.get("time") or "",
            )
            for item in (raw.get("lineup")) or []
        )
        tickets = tuple(
            Ticket(
                icon=item.get("icon", "local_activity"),
                icon_color=item.get("icon_color", "#89ceff"),
                name=item.get("name", ""),
                sub=item.get("sub", ""),
                price=item.get("price", "No price"),
                hover_color=item.get("hover_color", "#89ceff"),
            )
            for item in (raw.get("tickets")) or []
        )

        return Event(
            id=public_id,
            title=title,
            short_title=short_title,
            month=month,
            day=day,
            time=time_str,
            day_label=day_label,
            venue=raw.get("venue") or "",
            location=raw.get("location") or "",
            distance="",
            category=raw.get("category") or "All Events",
            category_color=raw.get("category_color") or "#7c3aed",
            price=raw.get("price_label") or "No price",
            image=raw.get("image_url") or "",
            tags=tags,
            lat=float(raw.get("lat") or 0.0),
            lng=float(raw.get("lng") or 0.0),
            map_pin_category=MapPinCategory.DEFAULT,
            featured=False,
            event_date=starts_dt.date(),
            description=raw.get("description") or "",
            lineup=lineup,
            tickets=tickets,
            is_community_event=True,
            created_by=raw.get("owner_username"),
        )

    def search_events(self, params: ProviderSearchParams) -> list[Event]:
        raw_list = self._client.list_published()
        events = []
        for raw in raw_list:
            try:
                events.append(self._map_to_event(raw))
            except Exception:
                logger.exception(
                    "CustomEventProvider: skipping malformed event id=%s", raw.get("id")
                )
        return events

    def get_event(self, external_id: str) -> Event | None:
        raw = self._client.get_event(external_id)
        if not raw:
            return None
        try:
            return self._map_to_event(raw)
        except Exception:
            logger.exception(
                "CustomEventProvider: failed to map event id=%s", external_id
            )
            return None
