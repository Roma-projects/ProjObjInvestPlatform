"""Для чего нужен этот файл:
Формирует поиск объявлений и применяет фильтры. Сервисный слой связывает API, проверку данных и хранилище.
"""

import hashlib
import json
import logging
import base64
import re
import asyncio
from typing import Any

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings
from app.schemas.search import SearchHit, SearchResponse, SuggestItem, SuggestResponse
from app.services.geocoding import geocoder

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    def __init__(self) -> None:
        self._index: dict[int, dict[str, Any]] = {}
        self._redis: aioredis.Redis | None = None
        self._mongo_client: AsyncIOMotorClient | None = None
        self._catalog = None
        self._blocked_sellers = None
        self._blocked_legacy_sellers = None
        self._blocked_legacy_owner_ids: set[int] = set()
        self._catalog_lock = asyncio.Lock()
        self._map_result_limit = 2000

    async def connect_redis(self) -> None:
        self._mongo_client = AsyncIOMotorClient(settings.mongodb_url)
        self._catalog = self._mongo_client.get_default_database().get_collection("listings")
        self._blocked_sellers = self._mongo_client.get_default_database().get_collection("blocked_sellers")
        self._blocked_legacy_sellers = self._mongo_client.get_default_database().get_collection("blocked_legacy_sellers")
        self._blocked_legacy_owner_ids = {
            int(row["_id"]) async for row in self._blocked_legacy_sellers.find({}, {"_id": 1})
        }
        await self._catalog.create_index("seller_id")
        await self._catalog.create_index([("location_point", "2dsphere")])
        await self._catalog.create_index([("status", 1), ("location_point.type", 1)])
        await self._catalog.create_index([("business_name", "text"), ("short_description", "text")])
        await self._catalog.create_index([("sale_price", 1), ("business_type", 1), ("verification_status", 1)])
        try:
            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            logger.info("Redis connected for search cache")
        except Exception as exc:
            logger.warning("Redis unavailable, cache disabled: %s", exc)
            self._redis = None
        geocoder.connect(self._mongo_client.get_default_database(), self._redis)

    async def close(self) -> None:
        await geocoder.close()
        if self._redis:
            await self._redis.close()
        if self._mongo_client:
            self._mongo_client.close()

    def upsert(self, listing: dict[str, Any]) -> None:
        if int(listing.get("owner_id", -1)) in self._blocked_legacy_owner_ids:
            logger.info("Ignoring legacy catalog upsert for blocked owner=%s", listing.get("owner_id"))
            return
        listing_id = int(listing["listing_id"])
        self._index[listing_id] = listing
        logger.debug("Index upsert listing_id=%s", listing_id)

    def delete(self, listing_id: int) -> None:
        self._index.pop(listing_id, None)
        logger.debug("Index delete listing_id=%s", listing_id)

    async def upsert_business(self, body: dict[str, Any]) -> None:
        """Store only allow-listed public fields from a completed listing event."""
        if self._catalog is None or self._blocked_sellers is None:
            raise RuntimeError("MongoDB catalog is not connected")
        incoming_public = dict(body.get("public_data") or {})
        public = dict(incoming_public)
        seller_id = str(public.get("seller_id") or body.get("user_id") or "")
        if not seller_id:
            logger.warning("Ignoring catalog upsert without seller id listing_id=%s", body.get("listing_id"))
            return
        allowed = {
            "seller_id", "seller_name", "business_name", "short_description", "business_type", "sale_price",
            "full_description", "stock_included", "stock_value", "area_sqm", "floor_number",
            "has_separate_entrance", "parking_spaces", "ceiling_height", "equipment_list",
            "staff_count", "staff_details", "working_hours", "business_age_months", "has_licenses",
            "has_contracts", "sale_reason", "stay_as_consultant_months", "monthly_financials",
            "average_check", "monthly_orders", "monthly_clients_unique", "cost_structure",
            "seasonality_months", "peak_hours", "supplier_contracts", "supplier_details",
            "debts_receivable", "debts_payable", "legal_claims", "legal_claims_details",
            "equipment_lease", "monthly_loan_payments", "customer_base_size", "repeat_customer_rate",
            "avg_monthly_revenue", "location", "photos", "main_photo", "video",
            "floor_plan_image",
            "deal_composition", "property_type", "property_condition",
            "transfer_method", "revenue_trend", "verification_status", "user_analytics",
            "location_point", "coordinate_precision",
        }
        public = {key: value for key, value in public.items() if key in allowed}
        location = public.get("location") or {}
        if not isinstance(location, dict):
            location = {}
        public["location"] = location
        geocode_input = {
            **public,
            "latitude": incoming_public.get("latitude"),
            "longitude": incoming_public.get("longitude"),
        }
        explicit_point = bool(
            geocode_input.get("location_point")
            or location.get("coordinates")
            or location.get("lat") is not None
            or geocode_input.get("latitude") is not None
        )
        point = await geocoder.resolve(geocode_input)
        if point:
            public["location_point"] = point
            public["coordinate_precision"] = (
                "address" if explicit_point or location.get("street") or location.get("house") else "city"
            )
        else:
            public.pop("location_point", None)
            public.pop("coordinate_precision", None)
        async with self._catalog_lock:
            if await self._blocked_sellers.find_one({"_id": seller_id}):
                logger.info("Ignoring catalog upsert for blocked seller=%s", seller_id)
                return
            catalog_update = {"$set": {**public, "seller_id": seller_id, "status": "published"}}
            if not point:
                catalog_update["$unset"] = {"location_point": "", "coordinate_precision": ""}
            await self._catalog.update_one(
                {"_id": str(body["listing_id"])},
                catalog_update,
                upsert=True,
            )
        if self._redis:
            async for key in self._redis.scan_iter("search:*"):
                await self._redis.delete(key)

    async def block_seller(self, seller_id: str, reason: str = "") -> None:
        if self._catalog is None or self._blocked_sellers is None:
            raise RuntimeError("MongoDB catalog is not connected")
        async with self._catalog_lock:
            await self._blocked_sellers.update_one(
                {"_id": seller_id}, {"$set": {"reason": reason[:500]}}, upsert=True
            )
            await self._catalog.delete_many({"seller_id": seller_id})
        if self._redis:
            async for key in self._redis.scan_iter("search:*"):
                await self._redis.delete(key)

    async def unblock_seller(self, seller_id: str) -> None:
        if self._blocked_sellers is None:
            raise RuntimeError("MongoDB catalog is not connected")
        async with self._catalog_lock:
            await self._blocked_sellers.delete_one({"_id": seller_id})

    async def block_legacy_seller(self, owner_id: int) -> None:
        if self._blocked_legacy_sellers is None:
            raise RuntimeError("MongoDB catalog is not connected")
        self._blocked_legacy_owner_ids.add(owner_id)
        await self._blocked_legacy_sellers.update_one({"_id": owner_id}, {"$set": {"blocked": True}}, upsert=True)
        for listing_id, listing in list(self._index.items()):
            if int(listing.get("owner_id", -1)) == owner_id:
                self._index.pop(listing_id, None)
        if self._redis:
            async for key in self._redis.scan_iter("search:*"):
                await self._redis.delete(key)

    async def unblock_legacy_seller(self, owner_id: int) -> None:
        if self._blocked_legacy_sellers is None:
            raise RuntimeError("MongoDB catalog is not connected")
        self._blocked_legacy_owner_ids.discard(owner_id)
        await self._blocked_legacy_sellers.delete_one({"_id": owner_id})

    async def delete_business(self, listing_id: str) -> None:
        if self._catalog is None:
            raise RuntimeError("MongoDB catalog is not connected")
        await self._catalog.delete_one({"_id": str(listing_id)})
        if self._redis:
            async for key in self._redis.scan_iter("search:*"):
                await self._redis.delete(key)

    async def search_businesses(self, *, q: str | None, business_type: str | list[str] | None,
                                min_price: float | None, max_price: float | None,
                                verification_status: str | None, sort: str,
                                cursor: str | None, limit: int,
                                deal_composition: str | list[str] | None = None,
                                property_type: str | list[str] | None = None,
                                property_condition: str | list[str] | None = None,
                                transfer_method: str | list[str] | None = None,
                                revenue_trend: str | list[str] | None = None,
                                city: str | None = None) -> dict[str, Any]:
        """Filter public cards and return a stable cursor for the next page."""
        if self._catalog is None:
            raise RuntimeError("MongoDB catalog is not connected")
        criteria: dict[str, Any] = {"status": "published"}
        if q:
            criteria["$text"] = {"$search": q}
        for field, value in (
            ("business_type", business_type),
            ("deal_composition", deal_composition),
            ("property_type", property_type),
            ("property_condition", property_condition),
            ("transfer_method", transfer_method),
            ("revenue_trend", revenue_trend),
        ):
            if isinstance(value, list):
                values = [item for item in value if item]
                if values:
                    criteria[field] = values[0] if len(values) == 1 else {"$in": values}
            elif value:
                criteria[field] = value
        if city:
            criteria["location.city"] = {"$regex": re.escape(city.strip()), "$options": "i"}
        if verification_status:
            criteria["verification_status"] = verification_status
        if min_price is not None or max_price is not None:
            criteria["sale_price"] = {}
            if min_price is not None:
                criteria["sale_price"]["$gte"] = min_price
            if max_price is not None:
                criteria["sale_price"]["$lte"] = max_price
        orderings = {"price_asc": [("sale_price", 1), ("_id", 1)],
                     "price_desc": [("sale_price", -1), ("_id", 1)],
                     "newest": [("_id", -1)]}
        ordering = orderings[sort]
        if cursor:
            try:
                cursor_value = json.loads(base64.urlsafe_b64decode(cursor + "==").decode())
                last_id = cursor_value["id"]
                if sort == "newest":
                    criteria["_id"] = {"$lt": last_id}
                else:
                    field = "sale_price"
                    operator = "$gt" if sort == "price_asc" else "$lt"
                    criteria["$or"] = [
                        {field: {operator: cursor_value["price"]}},
                        {field: cursor_value["price"], "_id": {"$gt": last_id}},
                    ]
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError("Invalid catalog cursor") from exc
        rows = await self._catalog.find(criteria).sort(ordering).limit(limit + 1).to_list(limit + 1)
        has_more = len(rows) > limit
        last_page_row = rows[limit - 1] if has_more else None
        items = [{"listing_id": str(row.pop("_id")), **row} for row in rows[:limit]]
        next_cursor = None
        if has_more:
            last = last_page_row
            assert last is not None
            value = {"id": last["_id"]}
            if sort != "newest":
                value["price"] = last.get("sale_price", 0)
            next_cursor = base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
        return {"items": items, "next_cursor": next_cursor}

    async def get_business(self, listing_id: str) -> dict[str, Any] | None:
        """Return one published catalog record (the index contains public fields only)."""
        if self._catalog is None:
            raise RuntimeError("MongoDB catalog is not connected")
        row = await self._catalog.find_one({"_id": listing_id, "status": "published"})
        if row is None:
            return None
        row.pop("_id", None)
        return {"listing_id": listing_id, **row}

    async def map_businesses(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return small public map markers, never private Listing-service fields."""
        if self._catalog is None:
            raise RuntimeError("MongoDB catalog is not connected")
        filters = filters or {}
        criteria: dict[str, Any] = {"status": "published"}
        if filters.get("q"):
            criteria["$text"] = {"$search": filters["q"]}
        for field in ("business_type", "deal_composition", "property_type", "property_condition", "transfer_method", "revenue_trend"):
            value = filters.get(field)
            if isinstance(value, list):
                values = [item for item in value if item]
                if values:
                    criteria[field] = values[0] if len(values) == 1 else {"$in": values}
            elif value:
                criteria[field] = value
        city = filters.get("city")
        if city:
            criteria["location.city"] = {"$regex": re.escape(str(city).strip()), "$options": "i"}
        if filters.get("verification_status") and filters["verification_status"] != "all":
            criteria["verification_status"] = filters["verification_status"]
        price: dict[str, Any] = {}
        if filters.get("min_price") is not None:
            price["$gte"] = filters["min_price"]
        if filters.get("max_price") is not None:
            price["$lte"] = filters["max_price"]
        if price:
            criteria["sale_price"] = price

        total = await self._catalog.count_documents(criteria)
        marker_criteria = {**criteria, "location_point.type": "Point"}
        located_total = await self._catalog.count_documents(marker_criteria)
        rows = await self._catalog.find(
            marker_criteria,
            {"business_name": 1, "sale_price": 1, "location.city": 1, "location_point": 1,
             "coordinate_precision": 1},
        ).limit(self._map_result_limit).to_list(self._map_result_limit)
        items = []
        for row in rows:
            point = row.get("location_point") or {}
            coordinates = point.get("coordinates") or []
            if len(coordinates) != 2:
                continue
            try:
                longitude, latitude = float(coordinates[0]), float(coordinates[1])
            except (TypeError, ValueError):
                continue
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                continue
            items.append({
                "listing_id": str(row["_id"]),
                "business_name": row.get("business_name") or "Бизнес на продаже",
                "sale_price": float(row["sale_price"]) if row.get("sale_price") is not None else None,
                "city": (row.get("location") or {}).get("city"),
                "latitude": latitude,
                "longitude": longitude,
                "coordinate_precision": row.get("coordinate_precision", "address"),
            })
        return {
            "items": items,
            "total": located_total,
            "unlocated": max(0, total - located_total),
            "truncated": located_total > self._map_result_limit,
        }

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
