"""Rate-limited, cached forward geocoding for public business addresses."""

import asyncio
import hashlib
import logging
import time
import unicodedata
from typing import Any

import httpx
from motor.motor_asyncio import AsyncIOMotorCollection

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_NEXT_REQUEST_SCRIPT = """
local now_parts = redis.call('TIME')
local now = tonumber(now_parts[1]) * 1000 + math.floor(tonumber(now_parts[2]) / 1000)
local next_request = tonumber(redis.call('GET', KEYS[1]) or '0')
if next_request > now then
  return next_request - now
end
redis.call('SET', KEYS[1], now + tonumber(ARGV[1]), 'PX', tonumber(ARGV[1]) * 10)
return 0
"""


def _valid_coordinates(lat: Any, lon: Any) -> tuple[float, float] | None:
    try:
        latitude, longitude = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _clean_address(location: dict[str, Any]) -> tuple[str, str] | None:
    parts = [location.get(key) for key in ("house", "street", "city", "country")]
    values = [" ".join(str(value).split()) for value in parts if value and str(value).strip()]
    if not values:
        return None
    address = ", ".join(values)
    normalized = unicodedata.normalize("NFKC", address).casefold()
    key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return address, key


class NominatimGeocoder:
    """Geocodes only public listing locations; never receives seller documents."""

    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None
        self._cache: AsyncIOMotorCollection | None = None
        self._redis = None
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    def connect(self, database, redis_client) -> None:
        self._cache = database.get_collection("geocode_cache")
        self._redis = redis_client
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=4.0),
            headers={"User-Agent": settings.nominatim_user_agent},
            follow_redirects=True,
        )

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _wait_for_request_slot(self) -> None:
        interval = max(1000, settings.nominatim_min_interval_ms)
        if self._redis is not None:
            try:
                while True:
                    wait_ms = int(await self._redis.eval(
                        _NEXT_REQUEST_SCRIPT, 1, "geocoding:nominatim:next", interval
                    ))
                    if wait_ms <= 0:
                        return
                    await asyncio.sleep(wait_ms / 1000)
            except Exception as exc:
                logger.warning("Shared Nominatim limiter unavailable; using local limiter: %s", exc)

        # Local development fallback. Compose uses one Search instance by default;
        # Redis provides a shared limiter when the service has multiple processes.
        async with self._lock:
            wait_seconds = self._last_request_at + interval / 1000 - time.monotonic()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._last_request_at = time.monotonic()

    async def resolve(self, public_data: dict[str, Any]) -> dict[str, Any] | None:
        """Return a GeoJSON point or None when the public address cannot be placed."""
        location = public_data.get("location") or {}
        if not isinstance(location, dict):
            location = {}

        # Accept coordinates supplied by a trusted parser or a future listing form.
        supplied = public_data.get("location_point") or location.get("coordinates")
        if isinstance(supplied, dict):
            coordinates = supplied.get("coordinates") or [supplied.get("lon"), supplied.get("lat")]
            if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
                valid = _valid_coordinates(coordinates[1], coordinates[0])
                if valid:
                    return {"type": "Point", "coordinates": [valid[1], valid[0]]}
        valid = _valid_coordinates(
            public_data.get("latitude", location.get("lat")),
            public_data.get("longitude", location.get("lon", location.get("lng"))),
        )
        if valid:
            return {"type": "Point", "coordinates": [valid[1], valid[0]]}

        if not any(location.get(key) for key in ("house", "street", "city")):
            return None
        address_data = _clean_address(location)
        if not settings.nominatim_enabled or self._cache is None or self._http is None or not address_data:
            return None
        address, cache_key = address_data
        cached = await self._cache.find_one({"_id": cache_key})
        if cached is not None:
            return cached.get("location_point")

        try:
            await self._wait_for_request_slot()
            # A different worker may have populated the cache while this one waited.
            cached = await self._cache.find_one({"_id": cache_key})
            if cached is not None:
                return cached.get("location_point")
            response = await self._http.get(
                settings.nominatim_base_url,
                params={"q": address, "format": "jsonv2", "limit": 1},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            results = response.json()
            point = None
            precision = "city"
            if isinstance(results, list) and results:
                row = results[0]
                valid = _valid_coordinates(row.get("lat"), row.get("lon"))
                if valid:
                    point = {"type": "Point", "coordinates": [valid[1], valid[0]]}
                    if location.get("street") or location.get("house"):
                        precision = "address"
            await self._cache.update_one(
                {"_id": cache_key},
                {"$set": {"location_point": point, "precision": precision}},
                upsert=True,
            )
            return point
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            # Geocoding is an enrichment step; it must not hold up catalog publication.
            logger.warning("Nominatim lookup failed for cached address key %s: %s", cache_key[:12], exc)
            return None


geocoder = NominatimGeocoder()
