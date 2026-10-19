"""Для чего нужен этот файл:
Получает сообщения из RabbitMQ и обрабатывает события других сервисов, не требуя прямого HTTP-вызова.
"""

import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings
from app.services.search_service import search_service

logger = logging.getLogger(__name__)
settings = get_settings()

EXCHANGE_LISTINGS = "listings_events"
QUEUE_SEARCH = "search_index_queue"


class SearchConsumer:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            channel = await self._connection.channel()
            await channel.set_qos(prefetch_count=20)
            exchange = await channel.declare_exchange(
                EXCHANGE_LISTINGS, ExchangeType.TOPIC, durable=True
            )
            queue = await channel.declare_queue(QUEUE_SEARCH, durable=True)
            await queue.bind(exchange, routing_key="listing.*")

            # New business listings enter the catalog only after moderation approves them.
            business_exchange = await channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
            catalog_queue = await channel.declare_queue("search_catalog.index", durable=True)
            await catalog_queue.bind(business_exchange, routing_key="listing.creation.completed")

            async def _on_message(message: aio_pika.IncomingMessage) -> None:
                async with message.process():
                    try:
                        body = json.loads(message.body.decode("utf-8"))
                        event_type = body.get("event_type", "")
                        if event_type == "listing.creation.completed":
                            await search_service.upsert_business(body)
                            return
                        if event_type in ("listing.created", "listing.updated"):
                            search_service.upsert(body)
                        elif event_type == "listing.deleted":
                            search_service.delete(int(body["listing_id"]))
                    except Exception as exc:
                        logger.exception("Failed to process search event: %s", exc)

            await queue.consume(_on_message)
            await catalog_queue.consume(_on_message)
            logger.info("Search consumer listening on %s", QUEUE_SEARCH)
        except Exception as exc:
            logger.warning("Search consumer not started: %s", exc)

    async def stop(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()


consumer = SearchConsumer()
