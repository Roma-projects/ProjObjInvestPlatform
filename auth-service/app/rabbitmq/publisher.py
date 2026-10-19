"""Публикует безопасные события Auth для Notification через RabbitMQ."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthEventPublisher:
    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None
        self.exchange: aio_pika.Exchange | None = None

    async def connect(self) -> None:
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await self.connection.channel()
        self.exchange = await channel.declare_exchange("auth", ExchangeType.TOPIC, durable=True)

    async def close(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    async def publish_security_event(self, event_type: str, user_id: str, metadata: dict[str, Any] | None = None) -> None:
        if self.exchange is None:
            await self.connect()
        payload = {
            "event": "auth.security_event",
            "event_type": event_type,
            "event_id": str(uuid4()),
            "user_id": user_id,
            "metadata": metadata or {},
        }
        message = aio_pika.Message(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self.exchange.publish(message, routing_key="auth.security_event")


publisher = AuthEventPublisher()
