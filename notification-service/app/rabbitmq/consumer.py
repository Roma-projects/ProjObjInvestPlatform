"""Подписывает Notification на бизнес-события через RabbitMQ."""

import json
import logging

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationConsumer:
    """Читает события объявления, входа и сообщения, не вызывая другие сервисы."""

    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=20)
        listings = await channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
        auth = await channel.declare_exchange("auth", ExchangeType.TOPIC, durable=True)
        messaging = await channel.declare_exchange("messaging", ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(
            "notification.events", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "notification.events.dlq"},
        )
        await channel.declare_queue("notification.events.dlq", durable=True)
        for exchange, key in (
            (listings, "listing.*"), (auth, "auth.security_event"), (messaging, "message.new"),
        ):
            await queue.bind(exchange, routing_key=key)

        async def handle(message: aio_pika.IncomingMessage) -> None:
            async with message.process(requeue=False):
                body = json.loads(message.body.decode("utf-8"))
                await notification_service.send(body)

        await queue.consume(handle)
        logger.info("In-app notification consumer started")

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


consumer = NotificationConsumer()
