"""Для чего нужен этот файл:
Получает сообщения из RabbitMQ и обрабатывает события других сервисов, не требуя прямого HTTP-вызова.
"""

import json
import logging

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationConsumer:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None

    async def start(self) -> None:
        try:
            self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            channel = await self._connection.channel()
            await channel.set_qos(prefetch_count=20)

            # messages_events → notifications_queue
            msg_ex = await channel.declare_exchange(
                "messages_events", ExchangeType.TOPIC, durable=True
            )
            notif_q = await channel.declare_queue("notifications_queue", durable=True)
            await notif_q.bind(msg_ex, routing_key="message.*")

            # notifications fanout → email_notifications_queue
            fanout = await channel.declare_exchange(
                "notifications", ExchangeType.FANOUT, durable=True
            )
            email_q = await channel.declare_queue(
                "email_notifications_queue", durable=True
            )
            await email_q.bind(fanout)

            async def _handle(message: aio_pika.IncomingMessage) -> None:
                async with message.process():
                    try:
                        body = json.loads(message.body.decode("utf-8"))
                        if body.get("event_type") == "message.sent":
                            await notification_service.send(
                                {
                                    "user_id": body.get("receiver_id"),
                                    "channel": "email",
                                    "subject": "New message",
                                    "body": body.get("content", "")[:200],
                                    "meta": body,
                                }
                            )
                        else:
                            await notification_service.send(body)
                    except Exception as exc:
                        logger.exception("Notification failed: %s", exc)

            await notif_q.consume(_handle)
            await email_q.consume(_handle)
            logger.info("Notification consumers started")
        except Exception as exc:
            logger.warning("Notification consumer not started: %s", exc)

    async def stop(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()


consumer = NotificationConsumer()
