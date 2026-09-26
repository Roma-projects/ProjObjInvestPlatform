"""Для чего нужен этот файл:
Преобразует адрес в географические координаты, чтобы объект недвижимости можно было разместить на карте.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def geocode_address(address: str) -> tuple[float | None, float | None]:
    """Geocode address via Nominatim (OpenStreetMap)."""
    url = f"{settings.nominatim_url.rstrip('/')}/search"
    params = {"q": address, "format": "json", "limit": 1}
    headers = {"User-Agent": settings.nominatim_user_agent}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            if not data:
                logger.info("Geocode miss for address=%s", address)
                return None, None
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as exc:
        logger.warning("Geocoding failed: %s", exc)
        return None, None
