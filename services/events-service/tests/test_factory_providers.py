from unittest.mock import patch

import pytest

from events_app.config import Settings
from events_app.providers.factory import build_event_repository
from events_app.repositories.aggregator_repository import AggregatorEventRepository


def test_factory_requires_at_least_one_provider():
    settings = Settings(ticketmaster_api_key="", eventbrite_token="")
    with pytest.raises(RuntimeError, match="No event providers configured"):
        build_event_repository(settings)


def test_factory_registers_ticketmaster_and_eventbrite():
    settings = Settings(
        ticketmaster_api_key="tm-key",
        eventbrite_token="eb-token",
    )
    with patch(
        "events_app.providers.factory.TicketmasterClient",
    ) as tm_cls, patch(
        "events_app.providers.factory.EventbriteClient",
    ) as eb_cls:
        tm_cls.return_value = object()
        eb_cls.return_value = object()
        repo = build_event_repository(settings)

    assert isinstance(repo, AggregatorEventRepository)
    assert len(repo._providers) == 2
    assert {p.name for p in repo._providers} == {"ticketmaster", "eventbrite"}
