import json
import logging
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType
from sqlalchemy import delete, select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.business_listing import BlockedUser, BusinessListing
from app.models.listing import PropertyListing
from app.models.outbox import OutboxEvent
from app.services.business_listing_service import _public_data

logger = logging.getLogger(__name__)
settings = get_settings()


class ModerationEventsConsumer:
    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=20)
        exchange = await channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
        await channel.declare_queue("listing.moderation.events.dlq", durable=True)
        queue = await channel.declare_queue(
            "listing.moderation.events", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "listing.moderation.events.dlq"},
        )
        await queue.bind(exchange, routing_key="moderation.listing.*")
        await queue.bind(exchange, routing_key="moderation.user.*")

        async def handle(message: aio_pika.IncomingMessage) -> None:
            async with message.process(requeue=False):
                await self._apply(json.loads(message.body.decode("utf-8")))

        await queue.consume(handle)
        logger.info("Listing moderation event consumer started")

    async def _apply(self, event: dict) -> None:
        event_name = event.get("event", "")
        async with AsyncSessionLocal() as session:
            if event_name == "moderation.user.blacklisted":
                user_id = UUID(event["user_id"])
                blocked = await session.get(BlockedUser, user_id)
                if blocked is None:
                    session.add(BlockedUser(user_id=user_id, reason=str(event.get("reason", ""))[:500]))
                rows = (await session.scalars(select(BusinessListing).where(
                    BusinessListing.user_id == user_id
                ).with_for_update())).all()
                for row in rows:
                    if row.status == "published":
                        session.add(OutboxEvent(routing_key="listing.removed", payload={
                            "event": "listing.removed", "listing_id": str(row.id), "user_id": str(user_id),
                        }))
                    row.status = "blocked"
                legacy_user_id = event.get("legacy_user_id")
                if legacy_user_id is not None:
                    legacy_rows = (await session.scalars(select(PropertyListing).where(
                        PropertyListing.owner_id == int(legacy_user_id)
                    ).with_for_update())).all()
                    for listing in legacy_rows:
                        listing.status = "blocked"
                        session.add(OutboxEvent(routing_key="listing.deleted", payload={
                            "event_type": "listing.deleted", "listing_id": listing.id,
                            "owner_id": listing.owner_id,
                        }))
                await session.commit()
                return

            if event_name == "moderation.user.unblocked":
                await session.execute(delete(BlockedUser).where(BlockedUser.user_id == UUID(event["user_id"])))
                await session.commit()
                return

            listing_id = UUID(event["listing_id"])
            row = await session.scalar(select(BusinessListing).where(
                BusinessListing.id == listing_id
            ).with_for_update())
            if row is None:
                logger.warning("Moderation result for unknown listing %s", listing_id)
                return
            if await session.get(BlockedUser, row.user_id):
                row.status = "blocked"
                await session.commit()
                return
            reports = dict(row.analytics_results or {})
            applied = set(reports.get("moderation_result_event_ids", []))
            event_id = event.get("event_id")
            if event_id and event_id in applied:
                return
            if event_name == "moderation.listing.removed":
                if row.status not in {"published", "on_moderation"}:
                    return
                row.status = "removed"
                if not reports.get("removal_event_queued"):
                    session.add(OutboxEvent(routing_key="listing.removed", payload={
                        "event": "listing.removed",
                        "listing_id": str(row.id),
                        "user_id": str(row.user_id),
                        "user_safe_reason": event.get("user_safe_reason"),
                    }))
                    reports["removal_event_queued"] = True
            elif event_name == "moderation.listing.approved":
                if row.status != "on_moderation":
                    return
                row.status = "published"
                row.verification_status = event.get("verification_level") or "basic"
                if not reports.get("completion_event_queued"):
                    session.add(OutboxEvent(routing_key="listing.creation.completed", payload={
                        "event": "listing.creation.completed", "listing_id": str(row.id),
                        "user_id": str(row.user_id), "public_data": _public_data(row),
                    }))
                    reports["completion_event_queued"] = True
            elif event_name == "moderation.listing.rejected":
                row.status = "rejected"
                session.add(OutboxEvent(routing_key="listing.rejected", payload={
                    "event": "listing.rejected", "listing_id": str(row.id), "user_id": str(row.user_id),
                    "user_safe_reason": event.get("user_safe_reason") or "Объявление не прошло проверку. Проверьте данные и обратитесь в поддержку.",
                }))
            else:
                return
            if event_id:
                applied.add(event_id)
                reports["moderation_result_event_ids"] = sorted(applied)
            row.analytics_results = reports
            await session.commit()

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


moderation_consumer = ModerationEventsConsumer()

