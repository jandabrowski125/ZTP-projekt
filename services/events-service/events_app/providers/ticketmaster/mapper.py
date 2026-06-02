from datetime import date, datetime
from typing import Any

from events_app.domain.models import Event, LineupArtist, MapPinCategory, Ticket
from events_app.providers import missing_data as md
from events_app.providers.id_registry import public_id_for

DEFAULT_IMAGE = "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=1080&q=80"

SEGMENT_TO_CATEGORY: dict[str, str] = {
    "Music": "Music",
    "Sports": "Sports",
    "Arts & Theatre": "Arts",
    "Film": "Arts",
    "Miscellaneous": "Food & Drink",
}

SEGMENT_TO_PIN: dict[str, MapPinCategory] = {
    "Music": MapPinCategory.MUSIC,
    "Sports": MapPinCategory.SPORTS,
    "Arts & Theatre": MapPinCategory.DEFAULT,
    "Film": MapPinCategory.DEFAULT,
    "Miscellaneous": MapPinCategory.FOOD,
}

CATEGORY_COLORS: dict[str, str] = {
    "Music": "#7c3aed",
    "Sports": "#4ade80",
    "Arts": "#0ea5e9",
    "Food & Drink": "#ffb784",
    "Nightlife": "#00a2e6",
}


def map_ticketmaster_event(
    raw: dict[str, Any],
    *,
    provider: str = "ticketmaster",
    featured: bool = False,
) -> Event:
    external_id = str(raw.get("id") or "")
    public_id = public_id_for(provider, external_id)

    name = raw.get("name") or md.NO_TITLE
    short_title = _short_title(name)

    event_date, month, day, time_str, day_label = _parse_dates(raw)
    venue, location, lat, lng, distance = _parse_venue(raw)
    category, pin_category = _parse_category(raw)
    category_color = CATEGORY_COLORS.get(category, "#7c3aed")
    image = _pick_image(raw)
    price = _format_list_price(raw)
    tags = _build_tags(raw, category)
    description = _parse_description(raw)
    lineup = _parse_lineup(raw)
    tickets = _parse_tickets(raw)

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
        description=description,
        lineup=lineup,
        tickets=tickets,
    )


def ticketmaster_external_id(raw: dict[str, Any]) -> str:
    return str(raw.get("id") or "")


def _short_title(title: str, max_len: int = 28) -> str:
    if len(title) <= max_len:
        return title
    return title[: max_len - 1].rstrip() + "…"


def _parse_dates(raw: dict[str, Any]) -> tuple[date, str, str, str, str]:
    dates = raw.get("dates") or {}
    start = dates.get("start") or {}
    local_date_str = start.get("localDate")
    local_time_str = start.get("localTime")

    if local_date_str:
        try:
            event_date = date.fromisoformat(local_date_str)
        except ValueError:
            event_date = date.today()
    else:
        event_date = date.today()

    month = event_date.strftime("%b").upper()
    day = event_date.strftime("%d").lstrip("0") or event_date.strftime("%d")

    if start.get("dateTBA") or start.get("dateTBD"):
        time_str = md.NO_TIME
        day_label = f"Date TBA — {event_date.strftime('%b %d')}"
    elif local_time_str:
        try:
            parsed_time = datetime.strptime(local_time_str, "%H:%M:%S")
            time_str = parsed_time.strftime("%I:%M %p").lstrip("0")
        except ValueError:
            time_str = local_time_str
        day_label = event_date.strftime("%A, %b %d")
    else:
        time_str = md.NO_TIME
        day_label = event_date.strftime("%A, %b %d")

    return event_date, month, day, time_str, day_label


def _parse_venue(raw: dict[str, Any]) -> tuple[str, str, float, float, str]:
    embedded = raw.get("_embedded") or {}
    venues = embedded.get("venues") or []
    venue_raw = venues[0] if venues else {}

    venue_name = venue_raw.get("name") or md.NO_VENUE
    city = (venue_raw.get("city") or {}).get("name") or ""
    state = (venue_raw.get("state") or {}).get("stateCode") or ""
    location = ", ".join(part for part in (city, state) if part) or md.NO_LOCATION

    loc = venue_raw.get("location") or {}
    try:
        lat = float(loc.get("latitude") or 0.0)
        lng = float(loc.get("longitude") or 0.0)
    except (TypeError, ValueError):
        lat, lng = 0.0, 0.0

    distance_val = venue_raw.get("distance")
    units = venue_raw.get("units") or "miles"
    if distance_val is not None:
        try:
            distance = f"{float(distance_val):.1f} {units}"
        except (TypeError, ValueError):
            distance = md.NO_DISTANCE
    else:
        distance = md.NO_DISTANCE

    return venue_name, location, lat, lng, distance


def _parse_category(raw: dict[str, Any]) -> tuple[str, MapPinCategory]:
    classifications = raw.get("classifications") or []
    primary = next((c for c in classifications if c.get("primary")), None)
    if not primary and classifications:
        primary = classifications[0]

    segment_name = md.NO_CATEGORY
    if primary:
        segment = primary.get("segment") or {}
        segment_name = segment.get("name") or md.NO_CATEGORY

    fallback = segment_name if segment_name != md.NO_CATEGORY else "Arts"
    category = SEGMENT_TO_CATEGORY.get(segment_name, fallback)
    pin = SEGMENT_TO_PIN.get(segment_name, MapPinCategory.DEFAULT)
    return category, pin


def _pick_image(raw: dict[str, Any]) -> str:
    images = raw.get("images") or []
    if not images:
        return DEFAULT_IMAGE

    preferred_ratios = ("16_9", "3_2", "4_3")
    for ratio in preferred_ratios:
        for image in images:
            if image.get("ratio") == ratio and image.get("url"):
                return str(image["url"])

    for image in images:
        if image.get("url"):
            return str(image["url"])

    return DEFAULT_IMAGE


def _format_list_price(raw: dict[str, Any]) -> str:
    ranges = raw.get("priceRanges") or []
    if not ranges:
        return md.NO_PRICE

    first = ranges[0]
    currency = first.get("currency") or "USD"
    min_price = first.get("min")
    max_price = first.get("max")

    if min_price is None and max_price is None:
        return md.NO_PRICE
    if min_price == 0 and max_price == 0:
        return "Free"
    if min_price == max_price and min_price is not None:
        return f"${int(min_price)}" if currency == "USD" else f"{min_price} {currency}"
    if min_price is not None and max_price is not None:
        return f"${int(min_price)}–${int(max_price)}"
    return md.NO_PRICE


def _build_tags(raw: dict[str, Any], category: str) -> tuple[str, ...]:
    tags: list[str] = []
    if category and category != md.NO_CATEGORY:
        tags.append(category)

    classifications = raw.get("classifications") or []
    if classifications:
        genre = (classifications[0].get("genre") or {}).get("name")
        sub_genre = (classifications[0].get("subGenre") or {}).get("name")
        if genre and genre not in tags:
            tags.append(genre)
        if sub_genre and sub_genre not in tags:
            tags.append(sub_genre)

    if raw.get("url"):
        tags.append("Ticketmaster")

    return tuple(tags[:5]) if tags else (md.NO_TAG,)


def _parse_description(raw: dict[str, Any]) -> str:
    for key in ("info", "description", "pleaseNote"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return md.NO_DESCRIPTION


def _parse_lineup(raw: dict[str, Any]) -> tuple[LineupArtist, ...]:
    embedded = raw.get("_embedded") or {}
    attractions = embedded.get("attractions") or []
    if not attractions:
        return ()

    artists: list[LineupArtist] = []
    for index, attraction in enumerate(attractions):
        name = attraction.get("name") or md.NO_LINEUP
        role = "Headliner" if index == 0 else ""
        artists.append(
            LineupArtist(
                name=name,
                role=role,
                role_color="#89ceff" if role else "",
                time="" if role else md.NO_TIME,
            )
        )
    return tuple(artists)


def _parse_tickets(raw: dict[str, Any]) -> tuple[Ticket, ...]:
    tickets: list[Ticket] = []
    ranges = raw.get("priceRanges") or []

    for index, price_range in enumerate(ranges):
        min_price = price_range.get("min")
        max_price = price_range.get("max")
        currency = price_range.get("currency") or "USD"
        type_name = str(price_range.get("type") or "standard").replace("_", " ").title()

        if min_price is None and max_price is None:
            price_label = md.NO_PRICE
        elif min_price == max_price:
            price_label = f"${int(min_price)}" if min_price is not None else md.NO_PRICE
        else:
            price_label = f"${int(min_price)}–${int(max_price)}"

        icon_colors = ["#89ceff", "#d2bbff", "#ffb784"]
        tickets.append(
            Ticket(
                icon="local_activity",
                icon_color=icon_colors[index % len(icon_colors)],
                name=type_name or md.NO_TICKET_TYPE,
                sub=md.NO_TICKET,
                price=price_label if currency == "USD" else f"{price_label} {currency}",
                hover_color=icon_colors[index % len(icon_colors)],
            )
        )

    url = raw.get("url")
    if url and not tickets:
        tickets.append(
            Ticket(
                icon="local_activity",
                icon_color="#89ceff",
                name="Tickets",
                sub="Available on Ticketmaster",
                price=md.NO_PRICE,
                hover_color="#89ceff",
            )
        )

    return tuple(tickets)
