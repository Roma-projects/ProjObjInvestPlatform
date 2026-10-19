"""Сохраняет принятые Gateway сообщения и публикует событие для Notification."""

from __future__ import annotations

import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings
from app.store import store

logger = logging.getLogger(__name__)
settings = get_settings()


class MessagingConsumer:
    """Обрабатывает командную очередь с идемпотентностью по client_message_id."""

    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=20)
        exchange = await channel.declare_exchange("messaging", ExchangeType.TOPIC, durable=True)
        output = await channel.declare_exchange("messaging", ExchangeType.TOPIC, durable=True)
        await channel.declare_queue("messaging.in.dlq", durable=True)
        queue = await channel.declare_queue(
            "messaging.in", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "messaging.in.dlq"},
        )
        await queue.bind(exchange, routing_key="message.send")

        async def handle(message: aio_pika.IncomingMessage) -> None:
            command = json.loads(message.body.decode("utf-8"))
            try:
                saved = await store.create_message(command)
                notice = {
                    "event": "message.new", "event_id": saved["_id"],
                    "message_id": saved["_id"], "user_id": saved["receiver_id"],
                    "sender_id": saved["sender_id"], "conversation_id": saved["conversation_id"],
                }
                await output.publish(aio_pika.Message(
                    json.dumps(notice).encode(), content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=saved["_id"],
                ), routing_key="message.new", mandatory=True)
                await message.ack()
            except Exception as exc:
                attempt = int((message.headers or {}).get("x-retry-count", 0))
                if attempt >= 3:
                    logger.exception("Message processing exhausted retries")
                    await message.reject(requeue=False)
                    return
                await asyncio.sleep(0.5 * (3 ** attempt))
                headers = dict(message.headers or {})
                headers["x-retry-count"] = attempt + 1
                retry = aio_pika.Message(
                    message.body, headers=headers, content_type=message.content_type,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=message.message_id,
                )
                await exchange.publish(retry, routing_key="message.send")
                await message.ack()
                logger.warning("Message retry %s scheduled: %s", attempt + 1, exc)

        await queue.consume(handle)
        logger.info("Messaging command consumer started")

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


consumer = MessagingConsumer()
