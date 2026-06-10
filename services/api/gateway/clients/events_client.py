from datetime import date
from typing import Any

import httpx

from eventradar_common.internal_auth import internal_auth_headers


class EventsServiceClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        internal_token: str = "",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._internal_headers = internal_auth_headers(internal_token)

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
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {"sort": sort}
        if category:
            params["category"] = category
        if location:
            params["location"] = location
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if query:
            params["query"] = query
        if lat is not None:
            params["lat"] = str(lat)
        if lng is not None:
            params["lng"] = str(lng)
        if include_community:
            params["include_community"] = "true"

        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            response = await client.get(
                "/internal/v1/events",
                params=params,
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_event(self, event_id: int) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            response = await client.get(
                f"/internal/v1/events/{event_id}",
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_categories(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            response = await client.get(
                "/internal/v1/categories",
                headers=self._internal_headers,
            )
            response.raise_for_status()
            return response.json()
