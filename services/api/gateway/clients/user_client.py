from typing import Any

import httpx

from eventradar_common.internal_auth import internal_auth_headers


class UserServiceClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 15.0,
        internal_token: str = "",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._internal_headers = internal_auth_headers(internal_token)

    def _merge_headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        merged = dict(self._internal_headers)
        if headers:
            merged.update(headers)
        return merged

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            return await client.request(
                method,
                path,
                json=json,
                headers=self._merge_headers(headers),
            )

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
