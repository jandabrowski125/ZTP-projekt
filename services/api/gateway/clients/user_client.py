from typing import Any

import httpx


class UserServiceClient:
    def __init__(self, base_url: str, *, timeout: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            return await client.request(method, path, json=json, headers=headers)

    async def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/internal/v1/auth/register", json=payload)
        response.raise_for_status()
        return response.json()

    async def login(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/internal/v1/auth/login", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_me(self, authorization: str) -> dict[str, Any]:
        response = await self._request(
            "GET",
            "/internal/v1/users/me",
            headers={"Authorization": authorization},
        )
        response.raise_for_status()
        return response.json()

    async def update_me(self, authorization: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request(
            "PATCH",
            "/internal/v1/users/me",
            json=payload,
            headers={"Authorization": authorization},
        )
        response.raise_for_status()
        return response.json()

    async def list_favorites(self, authorization: str) -> list[dict[str, Any]]:
        response = await self._request(
            "GET",
            "/internal/v1/users/me/favorites",
            headers={"Authorization": authorization},
        )
        response.raise_for_status()
        return response.json()

    async def add_favorite(self, authorization: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/internal/v1/users/me/favorites",
            json=payload,
            headers={"Authorization": authorization},
        )
        response.raise_for_status()
        return response.json()

    async def remove_favorite(self, authorization: str, saved_id: str) -> None:
        response = await self._request(
            "DELETE",
            f"/internal/v1/users/me/favorites/{saved_id}",
            headers={"Authorization": authorization},
        )
        response.raise_for_status()

    async def list_past_events(self, authorization: str) -> list[dict[str, Any]]:
        response = await self._request(
            "GET",
            "/internal/v1/users/me/past-events",
            headers={"Authorization": authorization},
        )
        response.raise_for_status()
        return response.json()

    async def add_past_event(self, authorization: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/internal/v1/users/me/past-events",
            json=payload,
            headers={"Authorization": authorization},
        )
        response.raise_for_status()
        return response.json()

    async def create_custom_event(self, authorization: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/internal/v1/custom-events",
            json=payload,
            headers={"Authorization": authorization},
        )
        response.raise_for_status()
        return response.json()

    async def list_my_custom_events(self, authorization: str) -> list[dict[str, Any]]:
        response = await self._request(
            "GET",
            "/internal/v1/custom-events/mine",
            headers={"Authorization": authorization},
        )
        response.raise_for_status()
        return response.json()
