"""Собирает независимые отчёты и применяет правила статуса объявления."""

from __future__ import annotations

import json
import logging
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.business_listing import BusinessListing
from app.models.outbox import OutboxEvent
from app.services.business_listing_service import SENSITIVE_MODERATION_DOCUMENTS, _public_data

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisResultsConsumer:
    """Сохраняет scripts/AI-отчёты в PostgreSQL и запускает финальное решение."""

    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=20)
        exchange = await channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(
            "listing.results", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "listing.results.dlq"},
        )
        await channel.declare_queue("listing.results.dlq", durable=True)
        await queue.bind(exchange, routing_key="listing.*.analysis.completed")

        async def handle(message: aio_pika.IncomingMessage) -> None:
            async with message.process(requeue=False):
                await self._save(json.loads(message.body.decode("utf-8")))

        await queue.consume(handle)
        logger.info("Listing analysis result consumer started")

    async def _save(self, event: dict) -> None:
        listing_id = UUID(event["listing_id"])
        event_name = event.get("event", "")
        key = "scripts_report" if ".scripts." in event_name else "ai_report"
        async with AsyncSessionLocal() as session:
            row = await session.scalar(select(BusinessListing).where(BusinessListing.id == listing_id).with_for_update())
            if row is None:
                logger.warning("Ignoring analysis result for unknown listing %s", listing_id)
                return
            reports = dict(row.analytics_results or {})
            processed = set(reports.get("processed_event_ids", []))
            event_id = event.get("event_id")
            if event_id and event_id in processed:
                return
            report = {name: value for name, value in event.items()
                      if name not in {"event", "event_id", "correlation_id", "listing_id", "user_id"}}
            reports[key] = report
            if event_id:
                processed.add(event_id)
                reports["processed_event_ids"] = sorted(processed)
            row.analytics_results = reports
            if key == "scripts_report":
                row.revenue_trend = event.get("revenue_trend")
            ai_report = reports.get("ai_report")
            if ai_report and reports.get("scripts_report") and not reports.get("final_decision_applied"):
                has_sensitive_docs = bool(SENSITIVE_MODERATION_DOCUMENTS.intersection(row.documents or {}))
                if has_sensitive_docs:
                    row.status, row.verification_status = "on_moderation", "deep"
                elif ai_report.get("moderation_status") == "auto_ok":
                    row.status, row.verification_status = "published", "all"
                    if not reports.get("completion_event_queued"):
                        session.add(OutboxEvent(routing_key="listing.creation.completed", payload={
                            "event": "listing.creation.completed", "listing_id": str(row.id),
                            "user_id": str(row.user_id), "public_data": _public_data(row),
                        }))
                        reports["completion_event_queued"] = True
                else:
                    row.status, row.verification_status = "on_moderation", "basic"
                    session.add(OutboxEvent(routing_key="listing.on_moderation", payload={
                        "event": "listing.on_moderation", "listing_id": str(row.id),
                        "user_id": str(row.user_id), "verification_status": "basic",
                    }))
                reports["final_decision_applied"] = True
                row.analytics_results = reports
            await session.commit()

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


results_consumer = AnalysisResultsConsumer()
