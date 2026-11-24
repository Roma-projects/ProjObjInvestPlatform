"""Собирает независимые отчёты и применяет правила статуса объявления."""

from __future__ import annotations

import json
import logging
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.business_listing import BusinessListing
from app.models.outbox import OutboxEvent
from app.services.business_listing_service import SENSITIVE_MODERATION_DOCUMENTS

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
                row.status = "on_moderation"
                row.verification_status = (
                    "deep"
                    if has_sensitive_docs or ai_report.get("verification_level") == "deep"
                    else "basic"
                )
                if not reports.get("moderation_request_queued"):
                    snapshot_fields = (
                        "business_type", "property_type", "transfer_method", "deal_composition", "business_name",
                        "short_description", "full_description", "sale_price", "stock_included", "stock_value",
                        "country", "city", "street", "house", "area_sqm", "floor_number", "has_separate_entrance",
                        "parking_spaces", "ceiling_height", "property_condition", "equipment_list", "staff_count",
                        "staff_details", "working_hours", "business_age_months", "has_licenses", "has_contracts",
                        "sale_reason", "stay_as_consultant_months", "monthly_financials", "average_check",
                        "monthly_orders", "monthly_clients_unique", "cost_structure", "seasonality_months", "peak_hours",
                        "supplier_contracts", "supplier_details", "debts_receivable", "debts_payable", "legal_claims",
                        "legal_claims_details", "equipment_lease", "monthly_loan_payments", "customer_base_size",
                        "repeat_customer_rate", "seller_status", "seller_name", "seller_inn", "seller_ogrnip",
                    )
                    snapshot = {name: getattr(row, name) for name in snapshot_fields}
                    snapshot.update({
                        "id": str(row.id),
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "files": {
                            key: value for key, value in (row.files or {}).items()
                            if key in {"main_photo", "photos", "floor_plan_image", "video"}
                        },
                        "video_url": row.video_url,
                    })
                    snapshot = json.loads(json.dumps(snapshot, default=str))
                    session.add(OutboxEvent(routing_key="listing.moderation.requested", payload={
                        "event": "listing.moderation.requested",
                        "listing_id": str(row.id),
                        "user_id": str(row.user_id),
                        "verification_level": row.verification_status,
                        "listing_snapshot": snapshot,
                        "analytics_reports": {
                            "scripts_report": reports.get("scripts_report"),
                            "ai_report": reports.get("ai_report"),
                        },
                        # Preserve the exact normalized payload both analytics workers received.
                        # This lets moderators compare submitted fields with both reports.
                        "analytics_input": jsonable_encoder(_data_for_analytics(row)),
                        "document_refs": dict(row.documents or {}),
                    }))
                    reports["moderation_request_queued"] = True
                reports["final_decision_applied"] = True
                row.analytics_results = reports
            await session.commit()

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


results_consumer = AnalysisResultsConsumer()
