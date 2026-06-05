import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from events_app.providers.protocol import ProviderSearchParams

logger = logging.getLogger(__name__)

TM_SORT_MAP = {
    "date_asc": "date,asc",
    "date_desc": "date,desc",
    "price_asc": "date,asc",
}

# Discovery API v2: unit enum is "miles" | "km" only (not "kilometers").
TM_VALID_UNITS = frozenset({"miles", "km"})

UNIT_ALIASES: dict[str, str] = {
    "kilometers": "km",
    "kilometer": "km",
    "kms": "km",
    "mi": "miles",
    "mile": "miles",
}

CATEGORY_TO_CLASSIFICATION: dict[str, str | None] = {
    "All Events": None,
    "Music": "Music",
    "Sports": "Sports",
    "Arts": "Arts & Theatre",
    "Food & Drink": "Miscellaneous",
    "Nightlife": "Music",
}


def normalize_ticketmaster_unit(unit: str) -> str:
    """Map human-friendly unit names to Ticketmaster API values."""
    key = unit.strip().lower()
    normalized = UNIT_ALIASES.get(key, key)
    if normalized not in TM_VALID_UNITS:
        msg = f"Invalid Ticketmaster radius unit '{unit}'. Use 'km' or 'miles'."
        raise ValueError(msg)
    return normalized


def normalize_ticketmaster_locale(locale: str) -> str:
    """Ticketmaster expects lowercase locales (e.g. en-us, pl-pl)."""
    return locale.strip().lower()


class TicketmasterApiError(RuntimeError):
    """Raised when Ticketmaster returns a non-success HTTP status."""


class TicketmasterRateLimitError(TicketmasterApiError):
    """Ticketmaster spike-arrest / rate limit (HTTP 429)."""


@dataclass
class _CacheEntry:
    expires_at: float
    events: list[dict[str, Any]]


class TicketmasterClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        lat: float,
        lng: float,
        radius: int,
        unit: str,
        country_code: str,
        locale: str,
        page_size: int,
        timeout: float = 15.0,
        cache_ttl_seconds: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._lat = lat
        self._lng = lng
        self._radius = radius
        self._unit = normalize_ticketmaster_unit(unit)
        self._country_code = country_code.strip().upper()
        self._locale = normalize_ticketmaster_locale(locale)
        self._page_size = page_size
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
                events = self._fetch_search(params)
            except TicketmasterRateLimitError:
                stale = self._stale.get(cache_key)
                if stale is not None:
                    logger.warning(
                        "Ticketmaster rate limit (429); serving cached results for %s",
                        cache_key,
                    )
                    return list(stale)
                logger.warning("Ticketmaster rate limit (429); no cached results for %s", cache_key)
                return []

            self._store(cache_key, events)
            return events

    def get_event(self, external_id: str) -> dict[str, Any] | None:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(
                f"{self._base_url}/events/{external_id}.json",
                params={"apikey": self._api_key, "locale": self._locale},
            )
            if response.status_code == 404:
                return None
            self._raise_for_status(response, {"id": external_id})

        return response.json()

    def _fetch_search(self, params: ProviderSearchParams) -> list[dict[str, Any]]:
        lat = params.lat if params.lat is not None else self._lat
        lng = params.lng if params.lng is not None else self._lng

        query: dict[str, str | int] = {
            "apikey": self._api_key,
            # latlong is deprecated but still supported; geoPoint requires geohash encoding.
            "latlong": f"{lat},{lng}",
            "radius": str(self._radius),
            "unit": self._unit,
            "locale": self._locale,
            "size": self._page_size,
            "sort": TM_SORT_MAP.get(params.sort, "date,asc"),
        }

        if self._country_code:
            query["countryCode"] = self._country_code

        classification = CATEGORY_TO_CLASSIFICATION.get(params.category or "All Events")
        if classification:
            query["classificationName"] = classification

        if params.query:
            query["keyword"] = params.query
        elif params.location:
            query["keyword"] = params.location

        if params.date_from:
            query["startDateTime"] = f"{params.date_from.isoformat()}T00:00:00Z"
        if params.date_to:
            query["endDateTime"] = f"{params.date_to.isoformat()}T23:59:59Z"

        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(f"{self._base_url}/events.json", params=query)
            self._raise_for_status(response, query)

        payload = response.json()
        embedded = payload.get("_embedded") or {}
        events = embedded.get("events") or []
        return events if isinstance(events, list) else []

    def _cache_key(self, params: ProviderSearchParams) -> str:
        lat = params.lat if params.lat is not None else self._lat
        lng = params.lng if params.lng is not None else self._lng
        # Round so minor map pan deltas reuse the same cache entry (~100 m).
        lat_key = round(lat, 3)
        lng_key = round(lng, 3)
        return "|".join(
            [
                f"{lat_key},{lng_key}",
                str(self._radius),
                self._unit,
                self._country_code or "-",
                self._locale,
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

    def _raise_for_status(self, response: httpx.Response, context: dict[str, Any]) -> None:
        if response.is_success:
            return
        body = response.text[:800]
        safe_url = str(response.url).split("?", 1)[0]
        safe_context = {key: ("***" if key == "apikey" else value) for key, value in context.items()}
        if response.status_code == 429:
            raise TicketmasterRateLimitError(
                f"Ticketmaster API 429 for {safe_url}. Params: {safe_context}. Body: {body}"
            ) from None
        raise TicketmasterApiError(
            f"Ticketmaster API {response.status_code} for {safe_url}. "
            f"Params: {safe_context}. Body: {body}"
        ) from None
