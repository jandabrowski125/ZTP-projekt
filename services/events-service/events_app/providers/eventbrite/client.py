"""EventBrite API v3 client.

Public GET /v3/events/search/ was removed (HTTP 404/406 → EventbriteSearchUnavailableError).

When EVENTBRITE_ORGANIZATION_ID is set: GET /v3/organizations/{id}/events/ and
filter by venue coordinates within EVENTBRITE_RADIUS / EVENTBRITE_UNIT.
Without an org id, search is attempted once, then returns []. See README.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from events_app.providers.protocol import ProviderSearchParams

logger = logging.getLogger(__name__)

EB_VALID_UNITS = frozenset({"km", "miles"})

UNIT_ALIASES: dict[str, str] = {
    "kilometers": "km",
    "kilometer": "km",
    "kms": "km",
    "mi": "miles",
    "mile": "miles",
}

EB_SORT_MAP = {
    "date_asc": "date",
    "date_desc": "date",
    "price_asc": "date",
}

CATEGORY_TO_EB: dict[str, str | None] = {
    "All Events": None,
    "Music": "103",
    "Sports": "108",
    "Arts": "105",
    "Food & Drink": "110",
    "Nightlife": "103",
}


def normalize_eventbrite_unit(unit: str) -> str:
    key = unit.strip().lower()
    normalized = UNIT_ALIASES.get(key, key)
    if normalized not in EB_VALID_UNITS:
        msg = f"Invalid EventBrite radius unit '{unit}'. Use 'km' or 'miles'."
        raise ValueError(msg)
    return normalized


def format_eventbrite_date(value: date) -> str:
    """Organization events API expects YYYY-MM-DD (not ISO datetimes)."""
    return value.isoformat()


def format_location_within(radius: int, unit: str) -> str:
    return f"{radius}{normalize_eventbrite_unit(unit)}"


def radius_km(radius: int, unit: str) -> float:
    normalized = normalize_eventbrite_unit(unit)
    return float(radius) * 1.60934 if normalized == "miles" else float(radius)


class EventbriteApiError(RuntimeError):
    """Raised when Eventbrite returns a non-success HTTP status."""


class EventbriteRateLimitError(EventbriteApiError):
    """EventBrite rate limit (HTTP 429)."""


class EventbriteSearchUnavailableError(EventbriteApiError):
    """Public event search removed or denied (HTTP 404 / 406)."""


@dataclass
class _CacheEntry:
    expires_at: float
    events: list[dict[str, Any]]


class EventbriteClient:
    def __init__(
        self,
        *,
        token: str,
        base_url: str,
        lat: float,
        lng: float,
        radius: int,
        unit: str,
        page_size: int,
        organization_id: str = "",
        timeout: float = 15.0,
        cache_ttl_seconds: float = 60.0,
    ) -> None:
        self._token = token.strip()
        self._organization_id = organization_id.strip()
        self._base_url = base_url.rstrip("/")
        self._lat = lat
        self._lng = lng
        self._radius = radius
        self._unit = normalize_eventbrite_unit(unit)
        self._within = format_location_within(radius, unit)
        self._radius_km = radius_km(radius, unit)
        self._page_size = min(page_size, 50)
        self._timeout = timeout
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, _CacheEntry] = {}
        self._stale: dict[str, list[dict[str, Any]]] = {}
        self._locks_guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    def search_events(self, params: ProviderSearchParams) -> list[dict[str, Any]]:
        cache_key = self._cache_key(params)
        cached = self._get_fresh(cache_key)
        if cached is not None:
            return cached

        lock = self._lock_for(cache_key)
        with lock:
            cached = self._get_fresh(cache_key)
            if cached is not None:
                return cached

            try:
                if self._organization_id:
                    events = self._fetch_organization_events(params)
                else:
                    events = self._fetch_search(params)
            except EventbriteRateLimitError:
                stale = self._stale.get(cache_key)
                if stale is not None:
                    logger.warning(
                        "EventBrite rate limit (429); serving cached results for %s",
                        cache_key,
                    )
                    return list(stale)
                logger.warning(
                    "EventBrite rate limit (429); no cached results for %s",
                    cache_key,
                )
                return []
            except EventbriteSearchUnavailableError:
                logger.warning(
                    "EventBrite public search unavailable and no "
                    "EVENTBRITE_ORGANIZATION_ID; returning no results."
                )
                events = []

            self._store(cache_key, events)
            return events

    def get_event(self, external_id: str) -> dict[str, Any] | None:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(
                f"{self._base_url}/events/{external_id}/",
                headers=self._headers(),
                params={"expand": "venue,category,subcategory,ticket_classes,description"},
            )
            if response.status_code == 404:
                return None
            self._raise_for_status(response)

        payload = response.json()
        return payload if isinstance(payload, dict) else None

    def _fetch_search(self, params: ProviderSearchParams) -> list[dict[str, Any]]:
        lat = params.lat if params.lat is not None else self._lat
        lng = params.lng if params.lng is not None else self._lng

        query: dict[str, str | int] = {
            "location.latitude": str(lat),
            "location.longitude": str(lng),
            "location.within": self._within,
            "expand": "venue,category,subcategory,logo",
            "page_size": self._page_size,
            "sort_by": EB_SORT_MAP.get(params.sort, "date"),
        }

        category_id = CATEGORY_TO_EB.get(params.category or "All Events")
        if category_id:
            query["categories"] = category_id

        if params.query:
            query["q"] = params.query
        elif params.location:
            query["q"] = params.location

        if params.date_from:
            query["start_date.range_start"] = format_eventbrite_date(params.date_from)
        if params.date_to:
            query["start_date.range_end"] = format_eventbrite_date(params.date_to)

        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(
                f"{self._base_url}/events/search/",
                headers=self._headers(),
                params=query,
            )
            self._raise_for_status(response, allow_search_unavailable=True)

        payload = response.json()
        events = payload.get("events") if isinstance(payload, dict) else None
        return events if isinstance(events, list) else []

    def _fetch_organization_events(self, params: ProviderSearchParams) -> list[dict[str, Any]]:
        query: dict[str, str | int] = {
            "expand": "venue,category,logo",
            "time_filter": "current_future",
            "page_size": self._page_size,
            "order_by": "start_asc",
        }
        if params.date_from:
            query["start_date.range_start"] = format_eventbrite_date(params.date_from)
        if params.date_to:
            query["start_date.range_end"] = format_eventbrite_date(params.date_to)

        lat = params.lat if params.lat is not None else self._lat
        lng = params.lng if params.lng is not None else self._lng

        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(
                f"{self._base_url}/organizations/{self._organization_id}/events/",
                headers=self._headers(),
                params=query,
            )
            self._raise_for_status(response)

        payload = response.json()
        events = payload.get("events") or []
        if not isinstance(events, list):
            return []

        return self._filter_by_radius(events, lat, lng)

    def _filter_by_radius(
        self,
        events: list[dict[str, Any]],
        lat: float,
        lng: float,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for raw in events:
            venue = raw.get("venue") or {}
            if not isinstance(venue, dict):
                continue
            address = venue.get("address") or {}
            if not isinstance(address, dict):
                continue
            v_lat = _parse_coord(address.get("latitude"))
            v_lng = _parse_coord(address.get("longitude"))
            if v_lat is None or v_lng is None:
                continue
            if _haversine_km(lat, lng, v_lat, v_lng) <= self._radius_km:
                filtered.append(raw)
        return filtered

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def _cache_key(self, params: ProviderSearchParams) -> str:
        lat = params.lat if params.lat is not None else self._lat
        lng = params.lng if params.lng is not None else self._lng
        return "|".join(
            [
                self._organization_id or "search",
                f"{round(lat, 3)},{round(lng, 3)}",
                self._within,
                params.category or "",
                params.sort,
                params.query or "",
                params.location or "",
                params.date_from.isoformat() if params.date_from else "",
                params.date_to.isoformat() if params.date_to else "",
            ]
        )

    def _get_fresh(self, cache_key: str) -> list[dict[str, Any]] | None:
        entry = self._cache.get(cache_key)
        if entry is None or entry.expires_at <= time.monotonic():
            return None
        return list(entry.events)

    def _store(self, cache_key: str, events: list[dict[str, Any]]) -> None:
        snapshot = list(events)
        self._stale[cache_key] = snapshot
        self._cache[cache_key] = _CacheEntry(
            expires_at=time.monotonic() + self._cache_ttl_seconds,
            events=snapshot,
        )

    def _lock_for(self, cache_key: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(cache_key)
            if lock is None:
                lock = threading.Lock()
                self._locks[cache_key] = lock
            return lock

    def _raise_for_status(
        self,
        response: httpx.Response,
        *,
        allow_search_unavailable: bool = False,
    ) -> None:
        if response.is_success:
            return
        body = response.text[:800]
        url = str(response.request.url).split("?", 1)[0]
        if response.status_code == 429:
            raise EventbriteRateLimitError(
                f"EventBrite API 429 for {url}. Body: {body}"
            ) from None
        if allow_search_unavailable and response.status_code in (404, 406):
            raise EventbriteSearchUnavailableError(
                f"EventBrite API {response.status_code} for {url}. Body: {body}"
            ) from None
        raise EventbriteApiError(
            f"EventBrite API {response.status_code} for {url}. Body: {body}"
        ) from None


def _parse_coord(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))
