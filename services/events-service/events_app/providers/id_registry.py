import zlib
from threading import Lock


def public_id_for(provider: str, external_id: str) -> int:
    """Stable numeric id for the frontend (deterministic per provider + external id)."""
    return zlib.crc32(f"{provider}:{external_id}".encode()) & 0x7FFFFFFF


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
