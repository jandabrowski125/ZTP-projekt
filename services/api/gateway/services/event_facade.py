from datetime import date

from gateway.clients.events_client import EventsServiceClient
from gateway.dto.events import (
    CategoryDTO,
    EventDetailsDTO,
    EventsListResponseDTO,
    MapPinDTO,
)
from gateway.mappers.event_mapper import (
    to_category_dto,
    to_event_data_dto,
    to_event_details_dto,
    to_map_pin_dto,
)


class EventFacade:
    def __init__(self, client: EventsServiceClient) -> None:
        self._client = client

    async def list_events(
        self,
        *,
        category: str | None = None,
        location: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        query: str | None = None,
        sort: str = "date_asc",
        lat: float | None = None,
        lng: float | None = None,
        include_community: bool = False,
    ) -> EventsListResponseDTO:
        raw_events = await self._client.list_events(
            category=category,
            location=location,
            date_from=date_from,
            date_to=date_to,
            query=query,
            sort=sort,
            lat=lat,
            lng=lng,
            include_community=include_community,
        )
        items = [to_event_data_dto(item) for item in raw_events]
        return EventsListResponseDTO(items=items, total=len(items))

    async def get_event(self, event_id: int) -> EventDetailsDTO:
        raw = await self._client.get_event(event_id)
        return to_event_details_dto(raw)

    async def list_map_pins(
        self,
        *,
        category: str | None = None,
        location: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        lat: float | None = None,
        lng: float | None = None,
        include_community: bool = False,
    ) -> list[MapPinDTO]:
        raw_events = await self._client.list_events(
            category=category,
            location=location,
            date_from=date_from,
            date_to=date_to,
            lat=lat,
            lng=lng,
            include_community=include_community,
        )
        return [to_map_pin_dto(item) for item in raw_events]

    async def list_categories(self) -> list[CategoryDTO]:
        raw = await self._client.list_categories()
        return [to_category_dto(item) for item in raw]
