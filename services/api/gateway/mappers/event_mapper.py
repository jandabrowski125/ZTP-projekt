from typing import Any

from gateway.dto.events import (
    CategoryDTO,
    CustomEventResponseDTO,
    EventDataDTO,
    EventDetailsDTO,
    LineupArtistDTO,
    MapPinDTO,
    TicketDTO,
)


def to_event_data_dto(raw: dict[str, Any]) -> EventDataDTO:
    return EventDataDTO(
        id=raw["id"],
        title=raw["title"],
        shortTitle=raw["short_title"],
        month=raw["month"],
        day=raw["day"],
        time=raw["time"],
        dayLabel=raw["day_label"],
        venue=raw["venue"],
        location=raw["location"],
        distance=raw["distance"],
        category=raw["category"],
        categoryColor=raw["category_color"],
        price=raw["price"],
        image=raw["image"],
        tags=raw["tags"],
    )


def to_event_details_dto(raw: dict[str, Any]) -> EventDetailsDTO:
    base = to_event_data_dto(raw)
    return EventDetailsDTO(
        **base.model_dump(by_alias=True),
        description=raw["description"],
        lineup=[_lineup_item(item) for item in raw.get("lineup", [])],
        tickets=[_ticket_item(item) for item in raw.get("tickets", [])],
        isCommunityEvent=raw.get("is_community_event", False),
        createdBy=raw.get("created_by"),
        communityEventId=raw.get("community_event_id"),
    )


def to_map_pin_dto(raw: dict[str, Any]) -> MapPinDTO:
    return MapPinDTO(
        id=raw["id"],
        lat=raw["lat"],
        lng=raw["lng"],
        label=raw["short_title"],
        time=raw["time"].split("–")[0].strip() if "–" in raw["time"] else raw["time"],
        price=raw["price"],
        category=raw["map_pin_category"],
        featured=raw.get("featured") or None,
    )


def to_category_dto(raw: dict[str, Any]) -> CategoryDTO:
    return CategoryDTO(label=raw["label"], icon=raw["icon"])


def _lineup_item(raw: dict[str, Any]) -> LineupArtistDTO:
    return LineupArtistDTO(
        name=raw["name"],
        role=raw["role"],
        roleColor=raw["role_color"],
        time=raw["time"],
    )


def _ticket_item(raw: dict[str, Any]) -> TicketDTO:
    return TicketDTO(
        icon=raw["icon"],
        iconColor=raw["icon_color"],
        name=raw["name"],
        sub=raw["sub"],
        price=raw["price"],
        hoverColor=raw["hover_color"],
    )


def to_custom_event_dto(raw: dict[str, Any]) -> CustomEventResponseDTO:
    """Convert user-service custom event (snake_case) to CustomEventResponseDTO (camelCase)."""
    starts_at = raw.get("starts_at")
    ends_at = raw.get("ends_at")
    return CustomEventResponseDTO(
        id=str(raw["id"]),
        ownerUserId=str(raw["owner_user_id"]),
        ownerUsername=raw.get("owner_username"),
        title=raw["title"],
        shortTitle=raw.get("short_title"),
        description=raw.get("description"),
        venue=raw["venue"],
        location=raw["location"],
        lat=raw["lat"],
        lng=raw["lng"],
        category=raw["category"],
        categoryColor=raw.get("category_color", "#7c3aed"),
        priceLabel=raw.get("price_label"),
        imageUrl=raw.get("image_url"),
        tags=raw.get("tags") or [],
        startsAt=str(starts_at) if starts_at is not None else "",
        endsAt=str(ends_at) if ends_at is not None else None,
        status=raw.get("status", "draft"),
        lineup=raw.get("lineup") or [],
        tickets=raw.get("tickets") or [],
    )
