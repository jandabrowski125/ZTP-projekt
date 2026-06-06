from events_app.config import Settings
from events_app.providers.id_registry import EventIdRegistry
from events_app.providers.ticketmaster.client import TicketmasterClient
from events_app.providers.ticketmaster.provider import TicketmasterProvider
from events_app.repositories.aggregator_repository import AggregatorEventRepository
from events_app.repositories.protocol import EventRepository


def build_event_repository(settings: Settings) -> EventRepository:
    registry = EventIdRegistry()
    providers = []

    if settings.ticketmaster_api_key.strip():
        client = TicketmasterClient(
            api_key=settings.ticketmaster_api_key.strip(),
            base_url=settings.ticketmaster_base_url,
            lat=settings.ticketmaster_search_lat,
            lng=settings.ticketmaster_search_lng,
            radius=settings.ticketmaster_radius,
            unit=settings.ticketmaster_unit,
            country_code=settings.ticketmaster_country_code,
            locale=settings.ticketmaster_locale,
            page_size=settings.ticketmaster_page_size,
            cache_ttl_seconds=settings.ticketmaster_cache_ttl_seconds,
        )
        providers.append(TicketmasterProvider(client, registry))

    if not providers:
        msg = "No event providers configured. Set TICKETMASTER_API_KEY in .env"
        raise RuntimeError(msg)

    return AggregatorEventRepository(providers, registry)
