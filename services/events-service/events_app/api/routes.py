from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from events_app.api.date_validation import validate_date_range
from events_app.schemas.internal import CategorySchema, EventSchema
from events_app.services.event_service import EventService

router = APIRouter(prefix="/internal/v1")


def get_event_service() -> EventService:
    from events_app.main import event_service, init_event_service

    if event_service is None:
        return init_event_service()
    return event_service


@router.get("/events", response_model=list[EventSchema])
def list_events(
    category: str | None = Query(default=None),
    location: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    query: str | None = Query(default=None),
    sort: str = Query(default="date_asc"),
    lat: float | None = Query(default=None, description="Search center latitude"),
    lng: float | None = Query(default=None, description="Search center longitude"),
    service: EventService = Depends(get_event_service),
) -> list[EventSchema]:
    validate_date_range(date_from, date_to)
    events = service.list_events(
        category=category,
        location=location,
        date_from=date_from,
        date_to=date_to,
        query=query,
        sort=sort,
        lat=lat,
        lng=lng,
    )
    return [EventSchema.model_validate(e) for e in events]


@router.get("/events/{event_id}", response_model=EventSchema)
def get_event(
    event_id: int,
    service: EventService = Depends(get_event_service),
) -> EventSchema:
    try:
        event = service.get_event(event_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EventSchema.model_validate(event)


@router.get("/categories", response_model=list[CategorySchema])
def list_categories(
    service: EventService = Depends(get_event_service),
) -> list[CategorySchema]:
    categories = service.list_categories()
    return [CategorySchema.model_validate(c) for c in categories]
