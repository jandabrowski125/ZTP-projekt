from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import HTTPStatusError

from gateway.dto.events import (
    CategoryDTO,
    EventDetailsDTO,
    EventsListResponseDTO,
    MapPinDTO,
)
from gateway.services.event_facade import EventFacade

router = APIRouter(prefix="/api/v1")


def get_facade() -> EventFacade:
    from gateway.main import event_facade

    return event_facade


@router.get("/events", response_model=EventsListResponseDTO, response_model_by_alias=True)
async def list_events(
    category: str | None = Query(default=None, description='e.g. "Music" or "All Events"'),
    location: str | None = Query(default=None, description="Substring match on venue/location"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None, description="Search query (title, tags)"),
    sort: str = Query(default="date_asc", pattern="^(date_asc|date_desc|price_asc)$"),
    lat: float | None = Query(default=None, description="Search center latitude"),
    lng: float | None = Query(default=None, description="Search center longitude"),
    facade: EventFacade = Depends(get_facade),
) -> EventsListResponseDTO:
    try:
        return await facade.list_events(
            category=category,
            location=location,
            date_from=date_from,
            date_to=date_to,
            query=q,
            sort=sort,
            lat=lat,
            lng=lng,
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc


@router.get("/events/{event_id}", response_model=EventDetailsDTO, response_model_by_alias=True)
async def get_event(
    event_id: int,
    facade: EventFacade = Depends(get_facade),
) -> EventDetailsDTO:
    try:
        return await facade.get_event(event_id)
    except HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Event not found") from exc
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc


@router.get("/map/pins", response_model=list[MapPinDTO], response_model_by_alias=True)
async def list_map_pins(
    category: str | None = Query(default=None),
    location: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    facade: EventFacade = Depends(get_facade),
) -> list[MapPinDTO]:
    try:
        return await facade.list_map_pins(
            category=category,
            location=location,
            lat=lat,
            lng=lng,
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc


@router.get("/categories", response_model=list[CategoryDTO])
async def list_categories(
    facade: EventFacade = Depends(get_facade),
) -> list[CategoryDTO]:
    try:
        return await facade.list_categories()
    except HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
