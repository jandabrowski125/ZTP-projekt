import logging
from datetime import datetime, timezone
from typing import Any

from eventradar_common.timezone_utils import ensure_utc, format_time_12h, timezone_at, to_timezone

from events_app.domain.models import Event, LineupArtist, MapPinCategory, Ticket
from events_app.providers.custom.client import UserServiceCustomClient
from events_app.providers.id_registry import EventIdRegistry, public_id_for
from events_app.providers.protocol import ProviderSearchParams

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_starts_at(raw: dict[str, Any]) -> datetime:
    starts_at = raw.get("starts_at")
    if isinstance(starts_at, str):
        try:
            return ensure_utc(datetime.fromisoformat(starts_at.replace("Z", "+00:00")))
        except ValueError:
            return _now_utc()
    if isinstance(starts_at, datetime):
        return ensure_utc(starts_at)
    return _now_utc()


class CustomEventProvider:
    name = "custom"

    def __init__(self, client: UserServiceCustomClient, registry: EventIdRegistry) -> None:
        self._client = client
        self._registry = registry

    def _map_to_event(self, raw: dict[str, Any]) -> Event:
        external_id = raw.get("id")
        public_id = public_id_for(self.name, str(external_id))
        self._registry.register(self.name, str(external_id), public_id)

        starts_dt = _parse_starts_at(raw)
        lat = float(raw.get("lat") or 0.0)
        lng = float(raw.get("lng") or 0.0)
        event_tz = raw.get("event_timezone") or timezone_at(lat, lng)
        local_dt = to_timezone(starts_dt, event_tz)

        title = raw.get("title") or raw.get("short_title") or "Untitled"
        short_title = raw.get("short_title") or title[:80]
        month = local_dt.strftime("%b").upper()
        day = local_dt.strftime("%d").lstrip("0") or "1"
        time_str = format_time_12h(local_dt)
        day_label = local_dt.strftime("%A, %b %d")

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
            address_line=raw.get("address_line") or "",
            postal_code=raw.get("postal_code") or "",
            distance="",
            category=raw.get("category") or "All Events",
            category_color=raw.get("category_color") or "#7c3aed",
            price=raw.get("price_label") or "No price",
            image=raw.get("image_url") or "",
            tags=tags,
            lat=lat,
            lng=lng,
            map_pin_category=MapPinCategory.DEFAULT,
            featured=False,
            event_date=local_dt.date(),
            description=raw.get("description") or "",
            lineup=lineup,
            tickets=tickets,
            is_community_event=True,
            created_by=raw.get("owner_username"),
            community_event_id=str(external_id) if external_id else None,
            starts_at=starts_dt,
            event_timezone=event_tz,
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
        if raw.get("status") != "published":
            return None
        try:
            return self._map_to_event(raw)
        except Exception:
            logger.exception(
                "CustomEventProvider: failed to map event id=%s", external_id
            )
            return None
