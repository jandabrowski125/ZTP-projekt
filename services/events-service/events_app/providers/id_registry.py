from threading import Lock

from eventradar_common.event_ids import public_id_for

__all__ = ["public_id_for", "EventIdRegistry"]


class EventIdRegistry:
    """Maps public numeric ids to (provider_name, external_id) after search/get."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_public_id: dict[int, tuple[str, str]] = {}

    def register(self, provider: str, external_id: str, public_id: int) -> None:
        with self._lock:
            self._by_public_id[public_id] = (provider, external_id)

    def resolve(self, public_id: int) -> tuple[str, str] | None:
        with self._lock:
            return self._by_public_id.get(public_id)
