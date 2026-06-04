from events_app.domain.models import Event
from events_app.providers.eventbrite.client import EventbriteClient
from events_app.providers.eventbrite.mapper import eventbrite_external_id, map_eventbrite_event
from events_app.providers.id_registry import EventIdRegistry
from events_app.providers.protocol import ProviderSearchParams


class EventbriteProvider:
    name = "eventbrite"

    def __init__(self, client: EventbriteClient, registry: EventIdRegistry) -> None:
        self._client = client
        self._registry = registry

    def search_events(self, params: ProviderSearchParams) -> list[Event]:
        raw_events = self._client.search_events(params)
        events: list[Event] = []

        for index, raw in enumerate(raw_events):
            external_id = eventbrite_external_id(raw)
            if not external_id:
                continue
            event = map_eventbrite_event(
                raw,
                provider=self.name,
                featured=index == 0,
                search_lat=params.lat,
                search_lng=params.lng,
            )
            self._registry.register(self.name, external_id, event.id)
            events.append(event)

        return events

    def get_event(self, external_id: str) -> Event | None:
        raw = self._client.get_event(external_id)
        if not raw:
            return None
        event = map_eventbrite_event(raw, provider=self.name, featured=False)
        self._registry.register(self.name, external_id, event.id)
        return event
