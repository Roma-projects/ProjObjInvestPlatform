"""Для чего нужен этот файл:
Формирует поиск объявлений и применяет фильтры. Сервисный слой связывает API, проверку данных и хранилище.
"""

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings
from app.schemas.search import SearchHit, SearchResponse, SuggestItem, SuggestResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    def __init__(self) -> None:
        self._index: dict[int, dict[str, Any]] = {}
        self._redis: aioredis.Redis | None = None

    async def connect_redis(self) -> None:
        try:
            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            logger.info("Redis connected for search cache")
        except Exception as exc:
            logger.warning("Redis unavailable, cache disabled: %s", exc)
            self._redis = None

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()

    def upsert(self, listing: dict[str, Any]) -> None:
        listing_id = int(listing["listing_id"])
        self._index[listing_id] = listing
        logger.debug("Index upsert listing_id=%s", listing_id)

    def delete(self, listing_id: int) -> None:
        self._index.pop(listing_id, None)
        logger.debug("Index delete listing_id=%s", listing_id)

    def _score(self, item: dict[str, Any], q: str | None) -> float:
        if not q:
            return 1.0
        q_lower = q.lower()
        title = str(item.get("title", "")).lower()
        address = str(item.get("address", "")).lower()
        score = 0.0
        if q_lower in title:
            score += 3.0
        if q_lower in address:
            score += 2.0
        for token in q_lower.split():
            if token in title:
                score += 1.0
            if token in address:
                score += 0.5
        return score

    def _cache_key(self, **params: Any) -> str:
        raw = json.dumps(params, sort_keys=True, default=str)
        return "search:" + hashlib.sha256(raw.encode()).hexdigest()

    async def search(
        self,
        *,
        q: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        rooms: int | None = None,
        min_area: float | None = None,
        max_area: float | None = None,
        listing_type: str | None = None,
        lat_min: float | None = None,
        lat_max: float | None = None,
        lng_min: float | None = None,
        lng_max: float | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResponse:
        cache_params = {
            "q": q,
            "min_price": min_price,
            "max_price": max_price,
            "rooms": rooms,
            "min_area": min_area,
            "max_area": max_area,
            "type": listing_type,
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lng_min": lng_min,
            "lng_max": lng_max,
            "page": page,
            "page_size": page_size,
        }
        key = self._cache_key(**cache_params)
        if self._redis:
            try:
                cached = await self._redis.get(key)
                if cached:
                    data = json.loads(cached)
                    data["cached"] = True
                    return SearchResponse.model_validate(data)
            except Exception as exc:
                logger.warning("Cache read failed: %s", exc)

        hits: list[SearchHit] = []
        for item in self._index.values():
            if item.get("status") not in (None, "active"):
                continue
            if min_price is not None and float(item.get("price", 0)) < min_price:
                continue
            if max_price is not None and float(item.get("price", 0)) > max_price:
                continue
            if rooms is not None and int(item.get("rooms", 0)) != rooms:
                continue
            if min_area is not None and float(item.get("area", 0)) < min_area:
                continue
            if max_area is not None and float(item.get("area", 0)) > max_area:
                continue
            if listing_type and item.get("type") != listing_type:
                continue
            lat = item.get("lat")
            lng = item.get("lng")
            if lat_min is not None and (lat is None or float(lat) < lat_min):
                continue
            if lat_max is not None and (lat is None or float(lat) > lat_max):
                continue
            if lng_min is not None and (lng is None or float(lng) < lng_min):
                continue
            if lng_max is not None and (lng is None or float(lng) > lng_max):
                continue
            score = self._score(item, q)
            if q and score <= 0:
                continue
            hits.append(
                SearchHit(
                    listing_id=int(item["listing_id"]),
                    title=item.get("title", ""),
                    price=float(item.get("price", 0)),
                    area=float(item.get("area", 0)),
                    rooms=int(item.get("rooms", 0)),
                    address=item.get("address", ""),
                    lat=item.get("lat"),
                    lng=item.get("lng"),
                    type=item.get("type", "apartment"),
                    status=item.get("status", "active"),
                    score=score,
                )
            )

        hits.sort(key=lambda h: h.score, reverse=True)
        total = len(hits)
        start = (page - 1) * page_size
        page_items = hits[start : start + page_size]
        response = SearchResponse(items=page_items, total=total, query=q, cached=False)

        if self._redis:
            try:
                await self._redis.setex(
                    key,
                    settings.cache_ttl_seconds,
                    response.model_dump_json(),
                )
            except Exception as exc:
                logger.warning("Cache write failed: %s", exc)

        return response

    async def suggest(self, q: str, limit: int = 10) -> SuggestResponse:
        q_lower = q.lower().strip()
        if not q_lower:
            return SuggestResponse(suggestions=[])
        suggestions: list[SuggestItem] = []
        for item in self._index.values():
            title = str(item.get("title", ""))
            address = str(item.get("address", ""))
            if q_lower in title.lower() or q_lower in address.lower():
                suggestions.append(
                    SuggestItem(text=title, listing_id=int(item["listing_id"]))
                )
            if len(suggestions) >= limit:
                break
        return SuggestResponse(suggestions=suggestions)


search_service = SearchService()
