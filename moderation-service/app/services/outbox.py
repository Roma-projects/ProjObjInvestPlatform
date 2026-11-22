import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import ModerationOutboxEvent
from app.rabbitmq.publisher import publisher

logger = logging.getLogger(__name__)


async def run_outbox_dispatcher(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            async with AsyncSessionLocal() as session:
                now = datetime.now(timezone.utc)
                pending = (await session.scalars(
                    select(ModerationOutboxEvent)
                    .where(ModerationOutboxEvent.state == "pending", ModerationOutboxEvent.available_at <= now)
                    .order_by(ModerationOutboxEvent.created_at)
                    .limit(25)
                    .with_for_update(skip_locked=True)
                )).all()
                for item in pending:
                    item.payload.setdefault("event_id", str(item.id))
                    try:
                        if not await publisher.publish(item.routing_key, item.payload):
                            raise RuntimeError("RabbitMQ is unavailable")
                        item.state = "published"
                        item.published_at = now
                        item.last_error = None
                    except Exception as exc:
                        item.attempts += 1
                        item.last_error = str(exc)[:500]
                        # Do not drop a blacklist or catalog decision during a
                        # long broker outage; consumers are idempotent by event.
                        item.available_at = now + timedelta(seconds=min(300, 2 ** item.attempts))
                await session.commit()
        except Exception:
            logger.exception("Moderation outbox dispatch cycle failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except TimeoutError:
            pass

