import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

import pytest

from events_app.repositories.mock_repository import MockEventRepository
from events_app.services.event_service import EventService


@pytest.fixture(autouse=True)
def use_mock_repository_for_api_tests():
    """API route tests use in-memory mock data (no Ticketmaster calls)."""
    import events_app.main as main

    main.event_service = EventService(MockEventRepository())
    yield
    main.event_service = None
