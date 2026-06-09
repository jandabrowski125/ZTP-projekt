from datetime import date, datetime
from typing import Any

from events_app.domain.models import Event, LineupArtist, MapPinCategory, Ticket
from events_app.providers import missing_data as md
from events_app.providers.id_registry import public_id_for

from events_app.providers.ticketmaster.segments import (
    CATEGORY_COLORS,
    CATEGORY_TO_PIN,
    SEGMENT_ID_TO_CATEGORY,
)

DEFAULT_IMAGE = "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=1080&q=80"


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
    venue, location, address_line, postal_code, lat, lng, distance = _parse_venue(raw)
    category, pin_category = _parse_category(raw)
    category_color = CATEGORY_COLORS.get(category, "#7c3aed")
    image = _pick_image(raw)
    ticket_url = str(raw.get("url") or "")
    price = _format_list_price(raw, ticket_url=ticket_url)
    tags = _build_tags(raw, category)
    description = _parse_description(raw)
    lineup = _parse_lineup(raw)
    tickets = _parse_tickets(raw, ticket_url=ticket_url, list_price=price)

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
        address_line=address_line,
        postal_code=postal_code,
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
        ticket_url=ticket_url,
        provider=provider,
        external_id=external_id,
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


def _parse_venue(raw: dict[str, Any]) -> tuple[str, str, str, str, float, float, str]:
    embedded = raw.get("_embedded") or {}
    venues = embedded.get("venues") or []
    venue_raw = venues[0] if venues else {}

    venue_name = venue_raw.get("name") or md.NO_VENUE
    city = (venue_raw.get("city") or {}).get("name") or ""
    state = (venue_raw.get("state") or {}).get("stateCode") or ""
    country = (venue_raw.get("country") or {}).get("name") or ""
    country_code = (venue_raw.get("country") or {}).get("countryCode") or ""
    if city and state:
        location = f"{city}, {state}"
    elif city and country_code and country_code != "US":
        location = f"{city}, {country}" if country else city
    elif city:
        location = city
    else:
        location = md.NO_LOCATION

    address = venue_raw.get("address") or {}
    line1 = str(address.get("line1") or "").strip()
    line2 = str(address.get("line2") or "").strip()
    address_line = ", ".join(part for part in (line1, line2) if part)
    postal_code = str(venue_raw.get("postalCode") or "").strip()

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

    return venue_name, location, address_line, postal_code, lat, lng, distance


def _parse_category(raw: dict[str, Any]) -> tuple[str, MapPinCategory]:
    classifications = raw.get("classifications") or []
    primary = next((c for c in classifications if c.get("primary")), None)
    if not primary and classifications:
        primary = classifications[0]

    segment_id = ""
    segment_name = md.NO_CATEGORY
    if primary:
        segment = primary.get("segment") or {}
        segment_id = str(segment.get("id") or "")
        segment_name = segment.get("name") or md.NO_CATEGORY

    if segment_id in SEGMENT_ID_TO_CATEGORY:
        category = SEGMENT_ID_TO_CATEGORY[segment_id]
    elif segment_name != md.NO_CATEGORY:
        category = segment_name
    else:
        category = md.NO_CATEGORY

    pin = CATEGORY_TO_PIN.get(category, MapPinCategory.DEFAULT)
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


def _format_amount(value: float | int, currency: str) -> str:
    amount = int(value) if float(value).is_integer() else round(float(value), 2)
    if currency == "USD":
        return f"${amount}"
    if currency == "EUR":
        return f"€{amount}"
    if currency == "GBP":
        return f"£{amount}"
    if currency == "PLN":
        return f"{amount} zł"
    return f"{amount} {currency}"


def _format_price_range(min_price: float | int | None, max_price: float | int | None, currency: str) -> str:
    if min_price is None and max_price is None:
        return md.NO_PRICE
    if min_price == 0 and max_price == 0:
        return "Free"
    if min_price is not None and max_price is not None:
        if min_price == max_price:
            return _format_amount(min_price, currency)
        return f"{_format_amount(min_price, currency)}–{_format_amount(max_price, currency)}"
    if min_price is not None:
        return f"from {_format_amount(min_price, currency)}"
    if max_price is not None:
        return f"up to {_format_amount(max_price, currency)}"
    return md.NO_PRICE


def _format_list_price(raw: dict[str, Any], *, ticket_url: str = "") -> str:
    ranges = raw.get("priceRanges") or []
    if not ranges:
        return "See Ticketmaster" if ticket_url else md.NO_PRICE

    first = ranges[0]
    currency = str(first.get("currency") or "USD").upper()
    return _format_price_range(first.get("min"), first.get("max"), currency)


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


def _parse_tickets(
    raw: dict[str, Any],
    *,
    ticket_url: str = "",
    list_price: str = md.NO_PRICE,
) -> tuple[Ticket, ...]:
    tickets: list[Ticket] = []
    ranges = raw.get("priceRanges") or []

    for index, price_range in enumerate(ranges):
        min_price = price_range.get("min")
        max_price = price_range.get("max")
        currency = str(price_range.get("currency") or "USD").upper()
        type_name = str(price_range.get("type") or "standard").replace("_", " ").title()
        price_label = _format_price_range(min_price, max_price, currency)

        icon_colors = ["#89ceff", "#d2bbff", "#ffb784"]
        tickets.append(
            Ticket(
                icon="local_activity",
                icon_color=icon_colors[index % len(icon_colors)],
                name=type_name or md.NO_TICKET_TYPE,
                sub="Available on Ticketmaster",
                price=price_label,
                hover_color=icon_colors[index % len(icon_colors)],
                url=ticket_url,
            )
        )

    if ticket_url and not tickets:
        tickets.append(
            Ticket(
                icon="local_activity",
                icon_color="#89ceff",
                name="Tickets",
                sub="Available on Ticketmaster",
                price=list_price if list_price != md.NO_PRICE else "See Ticketmaster",
                hover_color="#89ceff",
                url=ticket_url,
            )
        )

    return tuple(tickets)
