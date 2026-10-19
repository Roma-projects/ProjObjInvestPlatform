"""Обрабатывает started-события и публикует независимый аналитический результат."""

import json
import logging

import aio_pika
from aio_pika import ExchangeType
from motor.motor_asyncio import AsyncIOMotorClient

from app.analysis import analyze
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScriptsConsumer:
    """Хранит свой отчёт в MongoDB и возвращает его Listing через событие."""

    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None
        self.mongo = AsyncIOMotorClient(settings.mongodb_url)

    async def start(self) -> None:
        self.collection = self.mongo.get_default_database()["analysis_results"]
        await self.collection.create_index("listing_id", unique=True)
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=10)
        exchange = await channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
        result_exchange = await channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(
            "analytic.scripts", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "analytic.scripts.dlq"},
        )
        await channel.declare_queue("analytic.scripts.dlq", durable=True)
        await queue.bind(exchange, routing_key="listing.creation.started")

        async def handle(message: aio_pika.IncomingMessage) -> None:
            async with message.process(requeue=False):
                body = json.loads(message.body.decode("utf-8"))
                listing_id = str(body["listing_id"])
                report = analyze(body.get("data_for_analytics") or {})
                await self.collection.update_one(
                    {"listing_id": listing_id}, {"$set": {"listing_id": listing_id, **report}}, upsert=True
                )
                result = {
                    "event": "listing.scripts.analysis.completed",
                    "event_id": f"{body.get('correlation_id', listing_id)}:scripts",
                    "correlation_id": body.get("correlation_id"),
                    "listing_id": listing_id,
                    **report,
                }
                await result_exchange.publish(aio_pika.Message(
                    json.dumps(result, ensure_ascii=False).encode(), content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT, message_id=result["event_id"],
                ), routing_key="listing.scripts.analysis.completed", mandatory=True)
        await queue.consume(handle)
        logger.info("Analytic Scripts consumer started")

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        self.mongo.close()


consumer = ScriptsConsumer()
