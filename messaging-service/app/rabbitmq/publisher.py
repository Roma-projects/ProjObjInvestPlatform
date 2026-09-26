"""Для чего нужен этот файл:
Публикует событие в RabbitMQ, чтобы другие микросервисы могли его обработать.
"""

import json
import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings
from app.models.message import Message

logger = logging.getLogger(__name__)
settings = get_settings()

EXCHANGE_MESSAGES = "messages_events"
EXCHANGE_NOTIFICATIONS = "notifications"


class MessagePublisher:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._exchange: aio_pika.Exchange | None = None
        self._notif_exchange: aio_pika.Exchange | None = None

    async def connect(self) -> bool:
        try:
            self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            channel = await self._connection.channel()
            self._exchange = await channel.declare_exchange(
                EXCHANGE_MESSAGES, ExchangeType.TOPIC, durable=True
            )
            queue = await channel.declare_queue("notifications_queue", durable=True)
            await queue.bind(self._exchange, routing_key="message.*")
            self._notif_exchange = await channel.declare_exchange(
                EXCHANGE_NOTIFICATIONS, ExchangeType.FANOUT, durable=True
            )
            email_q = await channel.declare_queue(
                "email_notifications_queue", durable=True
            )
            await email_q.bind(self._notif_exchange)
            logger.info("Message publisher connected")
            return True
        except Exception as exc:
            logger.warning("RabbitMQ publisher unavailable: %s", exc)
            return False

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def _publish(
        self, exchange: aio_pika.Exchange | None, routing_key: str, body: dict[str, Any]
    ) -> None:
        if exchange is None:
            ok = await self.connect()
            if not ok:
                return
            exchange = self._exchange if routing_key.startswith("message") else self._notif_exchange
        if exchange is None:
            return
        message = aio_pika.Message(
            body=json.dumps(body, default=str).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=routing_key)

    async def message_sent(self, msg: Message) -> None:
        body = {
            "event_type": "message.sent",
            "message_id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "content": msg.content,
        }
        await self._publish(self._exchange, "message.sent", body)
        notif = {
            "event_type": "notification",
            "user_id": msg.receiver_id,
            "channel": "email",
            "subject": "New message",
            "body": f"You have a new message from user {msg.sender_id}",
            "meta": {"message_id": msg.id},
        }
        await self._publish(self._notif_exchange, "", notif)


message_publisher = MessagePublisher()
