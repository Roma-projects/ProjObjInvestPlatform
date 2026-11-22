"""One-time, explicitly enabled geocoding for older published catalog records.

Run from search-service/ with:
    python -m scripts.geocode_existing_catalog --execute --limit 100
Without --execute the script only reports how many eligible records it found.
"""

import argparse
import asyncio
import logging

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings
from app.services.geocoding import geocoder


async def run(execute: bool, limit: int) -> None:
    settings = get_settings()
    mongo = AsyncIOMotorClient(settings.mongodb_url)
    database = mongo.get_default_database()
    collection = database.get_collection("listings")
    query = {
        "status": "published",
        "location_point": {"$exists": False},
        "location.city": {"$exists": True, "$ne": ""},
    }
    total = await collection.count_documents(query)
    print(f"Eligible public listings without coordinates: {total}")
    if not execute:
        print("Dry run only. Add --execute to geocode at most the requested limit.")
        mongo.close()
        return
    if not settings.nominatim_enabled:
        raise RuntimeError("Set NOMINATIM_ENABLED=true before running the backfill")

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis_client.ping()
    except Exception:
        logging.warning("Redis is unavailable; the process-local rate limiter will be used")
        await redis_client.close()
        redis_client = None
    geocoder.connect(database, redis_client)
    processed = located = 0
    try:
        async for row in collection.find(query, {"location": 1}).limit(limit):
            location = row.get("location") or {}
            point = await geocoder.resolve({"location": location})
            processed += 1
            if point:
                precision = "address" if location.get("street") or location.get("house") else "city"
                await collection.update_one(
                    {"_id": row["_id"], "status": "published"},
                    {"$set": {"location_point": point, "coordinate_precision": precision}},
                )
                located += 1
        print(f"Processed: {processed}; coordinates saved: {located}; no match: {processed - located}")
    finally:
        await geocoder.close()
        if redis_client is not None:
            await redis_client.aclose()
        mongo.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="One-time Nominatim backfill for the public catalog")
    parser.add_argument("--execute", action="store_true", help="perform geocoding and write coordinates")
    parser.add_argument("--limit", type=int, default=100, help="maximum listings to process (default: 100)")
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    asyncio.run(run(args.execute, args.limit))


if __name__ == "__main__":
    main()
