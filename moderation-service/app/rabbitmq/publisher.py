import json
import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ModerationPublisher:
    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.Channel | None = None
        self.exchange: aio_pika.Exchange | None = None

    async def connect(self) -> bool:
        try:
            self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            self.channel = await self.connection.channel()
            self.exchange = await self.channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
            return True
        except Exception:
            logger.exception("RabbitMQ publisher connection failed")
            self.connection = None
            self.channel = None
            self.exchange = None
            return False

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> bool:
        if self.exchange is None and not await self.connect():
            return False
        assert self.exchange is not None
        message = aio_pika.Message(
            json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=payload.get("event_id"),
        )
        await self.exchange.publish(message, routing_key=routing_key, mandatory=True)
        return True

    async def close(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


publisher = ModerationPublisher()

