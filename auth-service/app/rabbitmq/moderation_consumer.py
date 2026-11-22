import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType
from sqlalchemy import select, update

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.session import AuthSession
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class ModerationBlacklistConsumer:
    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=20)
        exchange = await channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
        await channel.declare_queue("auth.moderation.blacklist.dlq", durable=True)
        queue = await channel.declare_queue(
            "auth.moderation.blacklist", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "auth.moderation.blacklist.dlq"},
        )
        await queue.bind(exchange, routing_key="moderation.user.blacklisted")
        await queue.bind(exchange, routing_key="moderation.user.unblocked")

        async def handle(message: aio_pika.IncomingMessage) -> None:
            async with message.process(requeue=False):
                await self._apply(json.loads(message.body.decode("utf-8")))

        await queue.consume(handle)
        logger.info("Auth blacklist event consumer started")

    async def _apply(self, event: dict) -> None:
        user_id = UUID(event["user_id"])
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.user_id == user_id).with_for_update())
            if user is None:
                logger.warning("Blacklist event references unknown auth user %s", user_id)
                return
            if event.get("event") == "moderation.user.blacklisted":
                user.is_banned = True
                user.ban_reason = str(event.get("reason", ""))[:500]
                user.banned_at = datetime.now(timezone.utc)
                await session.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(is_revoked=True))
            else:
                user.is_banned = False
                user.ban_reason = None
                user.banned_at = None
            await session.commit()

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


moderation_consumer = ModerationBlacklistConsumer()

