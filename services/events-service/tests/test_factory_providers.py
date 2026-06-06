from unittest.mock import patch

import pytest

from events_app.config import Settings
from events_app.providers.factory import build_event_repository
from events_app.repositories.aggregator_repository import AggregatorEventRepository


def test_factory_requires_ticketmaster_api_key():
    settings = Settings(ticketmaster_api_key="")
    with pytest.raises(RuntimeError, match="No event providers configured"):
        build_event_repository(settings)


def test_factory_registers_ticketmaster():
    settings = Settings(ticketmaster_api_key="tm-key")
    with patch("events_app.providers.factory.TicketmasterClient") as tm_cls:
        tm_cls.return_value = object()
        repo = build_event_repository(settings)

    assert isinstance(repo, AggregatorEventRepository)
    assert len(repo._providers) == 1
    assert repo._providers[0].name == "ticketmaster"
