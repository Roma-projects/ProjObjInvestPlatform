"""Для чего нужен этот файл:
Публикует событие в RabbitMQ, чтобы другие микросервисы могли его обработать.
"""

"""RabbitMQ publisher for listing events. Gracefully degrades if broker is down."""

import json
import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EXCHANGE_BUSINESS_LISTINGS = "listings"


class ListingPublisher:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._business_exchange: aio_pika.Exchange | None = None
        self._parsers_exchange: aio_pika.Exchange | None = None

    async def connect(self) -> bool:
        try:
            self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            self._channel = await self._connection.channel()
            self._business_exchange = await self._channel.declare_exchange(
                EXCHANGE_BUSINESS_LISTINGS, ExchangeType.TOPIC, durable=True
            )
            self._parsers_exchange = await self._channel.declare_exchange("parsers", ExchangeType.TOPIC, durable=True)
            business_queues = (
                ("analytic.scripts", "listing.creation.started"),
                ("analytic.ai", "listing.creation.started"),
                ("listing.results", "listing.*.analysis.completed"),
                ("search_catalog.index", "listing.creation.completed"),
            )
            for queue_name, bind_key in business_queues:
                dead_letter = f"{queue_name}.dlq"
                await self._channel.declare_queue(dead_letter, durable=True)
                queue = await self._channel.declare_queue(
                    queue_name,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": "",
                        "x-dead-letter-routing-key": dead_letter,
                    },
                )
                await queue.bind(self._business_exchange, routing_key=bind_key)
            parser_dlq = await self._channel.declare_queue("parsers.tasks.dlq", durable=True)
            parser_queue = await self._channel.declare_queue(
                "parsers.tasks", durable=True,
                arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "parsers.tasks.dlq"},
            )
            await parser_queue.bind(self._parsers_exchange, routing_key="parsers.request.registry")
            logger.info("RabbitMQ publisher connected")
            return True
        except Exception as exc:
            logger.warning("RabbitMQ unavailable: %s", exc)
            self._connection = None
            self._channel = None
            self._business_exchange = None
            self._parsers_exchange = None
            return False

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def publish_business_event(self, routing_key: str, body: dict[str, Any]) -> bool:
        if self._business_exchange is None and not await self.connect():
            return False
        exchange = self._parsers_exchange if routing_key.startswith("parsers.") else self._business_exchange
        assert exchange is not None
        if routing_key == "parsers.request.registry":
            # The AI reply mailbox must exist before Parsers can complete its work.
            assert self._channel is not None
            await self._channel.declare_queue(
                str(body["reply_to"]), durable=True, arguments={"x-expires": 720000}
            )
        message = aio_pika.Message(
            body=json.dumps(body, default=str, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=body.get("event_id"),
        )
        await exchange.publish(message, routing_key=routing_key, mandatory=True)
publisher = ListingPublisher()
