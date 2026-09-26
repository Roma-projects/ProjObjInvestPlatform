"""Для чего нужен этот файл:
Публикует событие в RabbitMQ, чтобы другие микросервисы могли его обработать.
"""

"""RabbitMQ publisher for listing events. Gracefully degrades if broker is down."""

import json
import logging
from decimal import Decimal
from typing import Any

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings
from app.models.listing import Listing

logger = logging.getLogger(__name__)
settings = get_settings()

EXCHANGE_LISTINGS = "listings_events"


def _listing_payload(listing: Listing) -> dict[str, Any]:
    return {
        "listing_id": listing.id,
        "owner_id": listing.owner_id,
        "title": listing.title,
        "price": float(listing.price) if isinstance(listing.price, Decimal) else listing.price,
        "area": listing.area,
        "rooms": listing.rooms,
        "address": listing.address,
        "lat": listing.lat,
        "lng": listing.lng,
        "type": listing.type,
        "status": listing.status,
    }


class ListingPublisher:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._exchange: aio_pika.Exchange | None = None

    async def connect(self) -> bool:
        try:
            self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                EXCHANGE_LISTINGS, ExchangeType.TOPIC, durable=True
            )
            # Declare bound queues for topology consistency
            for queue_name, bind_key in (
                ("search_index_queue", "listing.*"),
                ("analytics_queue", "listing.*"),
            ):
                queue = await self._channel.declare_queue(queue_name, durable=True)
                await queue.bind(self._exchange, routing_key=bind_key)
            logger.info("RabbitMQ publisher connected")
            return True
        except Exception as exc:
            logger.warning("RabbitMQ unavailable: %s", exc)
            self._connection = None
            self._channel = None
            self._exchange = None
            return False

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def publish(self, routing_key: str, body: dict[str, Any]) -> None:
        if self._exchange is None:
            ok = await self.connect()
            if not ok:
                logger.warning("Skip publish %s (no broker)", routing_key)
                return
        assert self._exchange is not None
        message = aio_pika.Message(
            body=json.dumps(body, default=str).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=routing_key)
        logger.info("Published %s listing_id=%s", routing_key, body.get("listing_id"))

    async def listing_created(self, listing: Listing) -> None:
        payload = {"event_type": "listing.created", **_listing_payload(listing)}
        await self.publish("listing.created", payload)

    async def listing_updated(self, listing: Listing) -> None:
        payload = {"event_type": "listing.updated", **_listing_payload(listing)}
        await self.publish("listing.updated", payload)

    async def listing_deleted(self, listing_id: int, owner_id: int) -> None:
        await self.publish(
            "listing.deleted",
            {
                "event_type": "listing.deleted",
                "listing_id": listing_id,
                "owner_id": owner_id,
            },
        )


publisher = ListingPublisher()
