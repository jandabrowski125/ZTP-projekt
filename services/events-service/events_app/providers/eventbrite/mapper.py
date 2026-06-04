from datetime import date, datetime
from typing import Any

from events_app.domain.models import Event, MapPinCategory
from events_app.providers import missing_data as md
from events_app.providers.id_registry import public_id_for

DEFAULT_IMAGE = "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=1080&q=80"

CATEGORY_COLORS: dict[str, str] = {
    "Music": "#7c3aed",
    "Sports": "#4ade80",
    "Arts": "#0ea5e9",
    "Food & Drink": "#ffb784",
    "Nightlife": "#00a2e6",
}


def map_eventbrite_event(
    raw: dict[str, Any],
    *,
    provider: str = "eventbrite",
    featured: bool = False,
    search_lat: float | None = None,
    search_lng: float | None = None,
) -> Event:
    external_id = str(raw.get("id") or "")
    public_id = public_id_for(provider, external_id)

    name = _event_name(raw)
    short_title = _short_title(name)
    event_date, month, day, time_str, day_label = _parse_dates(raw)
    venue, location, lat, lng, distance = _parse_venue(raw, search_lat, search_lng)
    category = _parse_category(raw)
    category_color = CATEGORY_COLORS.get(category, "#7c3aed")
    pin_category = _pin_for_category(category)
    image = _pick_image(raw)
    price = _format_list_price(raw)
    tags = _build_tags(raw, category)

    return Event(
        id=public_id,
        title=name,
        short_title=short_title,
        month=month,
        day=day,
        time=time_str,
        day_label=day_label,
        venue=venue,
        location=location,
        distance=distance,
        category=category,
        category_color=category_color,
        price=price,
        image=image,
        tags=tags,
        lat=lat,
        lng=lng,
        map_pin_category=pin_category,
        featured=featured,
        event_date=event_date,
        description=_parse_description(raw),
        lineup=(),
        tickets=_parse_tickets(raw),
    )


def eventbrite_external_id(raw: dict[str, Any]) -> str | None:
    event_id = raw.get("id")
    return str(event_id) if event_id else None


def _event_name(raw: dict[str, Any]) -> str:
    name = raw.get("name")
    if isinstance(name, dict):
        return str(name.get("text") or md.NO_TITLE)
    if isinstance(name, str):
        return name
    return md.NO_TITLE


def _short_title(title: str, max_len: int = 28) -> str:
    if len(title) <= max_len:
        return title
    return f"{title[: max_len - 1].rstrip()}…"


def _parse_dates(raw: dict[str, Any]) -> tuple[date, str, str, str, str]:
    start = raw.get("start") or {}
    local = start.get("local") if isinstance(start, dict) else None
    if isinstance(local, str) and len(local) >= 10:
        try:
            dt = datetime.fromisoformat(local.replace("Z", ""))
            event_date = dt.date()
            month = event_date.strftime("%b").upper()
            day = str(event_date.day)
            time_str = dt.strftime("%I:%M %p").lstrip("0")
            day_label = event_date.strftime("%A, %b %d")
            return event_date, month, day, time_str, day_label
        except ValueError:
            pass
    today = date.today()
    day_label = today.strftime("%A, %b %d")
    return today, today.strftime("%b").upper(), str(today.day), md.NO_TIME, day_label


def _parse_venue(
    raw: dict[str, Any],
    search_lat: float | None,
    search_lng: float | None,
) -> tuple[str, str, float, float, str]:
    venue = raw.get("venue") or {}
    if not isinstance(venue, dict):
        return md.NO_VENUE, md.NO_LOCATION, 0.0, 0.0, md.NO_DISTANCE

    venue_name = str(venue.get("name") or md.NO_VENUE)
    address = venue.get("address") or {}
    city = ""
    if isinstance(address, dict):
        city = str(address.get("city") or address.get("localized_area_display") or "")
    location = city or md.NO_LOCATION

    lat = _coord(address.get("latitude") if isinstance(address, dict) else None)
    lng = _coord(address.get("longitude") if isinstance(address, dict) else None)
    distance = md.NO_DISTANCE
    if search_lat is not None and search_lng is not None and lat and lng:
        distance = _format_distance_km(search_lat, search_lng, lat, lng)

    return venue_name, location, lat, lng, distance


def _coord(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> str:
    import math

    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    km = 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    if km < 1:
        return f"{int(km * 1000)} METERS"
    return f"{km:.1f} KILOMETERS"


def _parse_category(raw: dict[str, Any]) -> str:
    category = raw.get("category") or {}
    if isinstance(category, dict):
        name = category.get("name") or category.get("short_name")
        if isinstance(name, str) and name:
            lowered = name.lower()
            if "music" in lowered:
                return "Music"
            if "food" in lowered or "drink" in lowered:
                return "Food & Drink"
            if "sport" in lowered:
                return "Sports"
            if "art" in lowered or "theatre" in lowered or "theater" in lowered:
                return "Arts"
    return "Music"


def _pin_for_category(category: str) -> MapPinCategory:
    if category == "Sports":
        return MapPinCategory.SPORTS
    if category == "Food & Drink":
        return MapPinCategory.FOOD
    if category == "Arts":
        return MapPinCategory.DEFAULT
    return MapPinCategory.MUSIC


def _pick_image(raw: dict[str, Any]) -> str:
    logo = raw.get("logo") or {}
    if isinstance(logo, dict):
        url = logo.get("url")
        if isinstance(url, str) and url:
            return url
    return DEFAULT_IMAGE


def _parse_description(raw: dict[str, Any]) -> str:
    description = raw.get("description") or {}
    if isinstance(description, dict):
        text = description.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    if isinstance(description, str) and description.strip():
        return description.strip()
    return md.NO_DESCRIPTION


def _format_list_price(raw: dict[str, Any]) -> str:
    if raw.get("is_free") is True:
        return "Free"
    ticket_classes = raw.get("ticket_classes")
    if not isinstance(ticket_classes, list) or not ticket_classes:
        return md.NO_PRICE

    costs: list[float] = []
    currency = "USD"
    for ticket_class in ticket_classes:
        if not isinstance(ticket_class, dict):
            continue
        cost = ticket_class.get("cost")
        if isinstance(cost, dict):
            major = cost.get("major_value")
            currency = cost.get("currency") or currency
            if major is not None:
                try:
                    costs.append(float(major))
                except (TypeError, ValueError):
                    pass
    if not costs:
        return md.NO_PRICE
    low, high = min(costs), max(costs)
    if low == high:
        return f"${int(low)}" if currency == "USD" else f"{low} {currency}"
    return f"${int(low)}–${int(high)}" if currency == "USD" else f"{low}–{high} {currency}"


def _parse_tickets(raw: dict[str, Any]) -> tuple:
    from events_app.domain.models import Ticket

    ticket_classes = raw.get("ticket_classes")
    if not isinstance(ticket_classes, list):
        url = raw.get("url")
        if url:
            return (
                Ticket(
                    icon="local_activity",
                    icon_color="#89ceff",
                    name="Tickets",
                    sub="Available on Eventbrite",
                    price=md.NO_PRICE,
                    hover_color="#89ceff",
                ),
            )
        return ()

    tickets: list[Ticket] = []
    icon_colors = ["#89ceff", "#d2bbff", "#ffb784"]
    for index, ticket_class in enumerate(ticket_classes):
        if not isinstance(ticket_class, dict):
            continue
        name = ticket_class.get("name") or md.NO_TICKET_TYPE
        cost = ticket_class.get("cost") if isinstance(ticket_class.get("cost"), dict) else {}
        currency = cost.get("currency") or "USD"
        major = cost.get("major_value")
        if ticket_class.get("free") is True:
            price_label = "Free"
        elif major is not None:
            try:
                price_label = (
                    f"${int(float(major))}"
                    if currency == "USD"
                    else f"{major} {currency}"
                )
            except (TypeError, ValueError):
                price_label = md.NO_PRICE
        else:
            price_label = md.NO_PRICE
        color = icon_colors[index % len(icon_colors)]
        tickets.append(
            Ticket(
                icon="local_activity",
                icon_color=color,
                name=str(name),
                sub=md.NO_TICKET,
                price=price_label,
                hover_color=color,
            )
        )
    return tuple(tickets)


def _build_tags(raw: dict[str, Any], category: str) -> tuple[str, ...]:
    tags = [category, "Eventbrite"]
    if raw.get("is_free"):
        tags.append("Free")
    return tuple(tags)
