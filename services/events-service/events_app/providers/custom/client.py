from typing import Any

import httpx


class UserServiceCustomClient:
    def __init__(self, base_url: str, *, internal_token: str = "", timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._internal_token = internal_token

    def _auth_headers(self) -> dict[str, str]:
        if self._internal_token:
            return {"X-Internal-Service-Token": self._internal_token}
        return {}

    def list_published(self) -> list[dict[str, Any]]:
        """Return list of published custom events from user-service (synchronous)."""
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(
                f"{self._base}/internal/v1/custom-events/published",
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(
                f"{self._base}/internal/v1/custom-events/{event_id}",
                headers=self._auth_headers(),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

