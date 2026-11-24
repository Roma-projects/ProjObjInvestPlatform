import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import BlacklistEntry, ModerationCase, ModerationOutboxEvent

logger = logging.getLogger(__name__)
settings = get_settings()
PRIVATE_DOCUMENT_FIELDS = {
    "evacuation_plan_doc", "fire_declaration_doc", "fire_service_contract_doc", "san_epid_conclusion",
    "tax_certificate_doc", "income_statement_doc", "lease_agreement_doc", "ownership_doc", "passport_copy_doc",
}
SENSITIVE_DOCUMENT_FIELDS = {"passport_copy_doc", "tax_certificate_doc", "income_statement_doc"}


class ModerationConsumer:
    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=20)
        exchange = await channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
        await channel.declare_queue("moderation.inbox.dlq", durable=True)
        queue = await channel.declare_queue(
            "moderation.inbox", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "moderation.inbox.dlq"},
        )
        await queue.bind(exchange, routing_key="listing.moderation.requested")

        async def handle(message: aio_pika.IncomingMessage) -> None:
            async with message.process(requeue=False):
                await self._create_case(json.loads(message.body.decode("utf-8")))

        await queue.consume(handle)
        logger.info("Moderation event consumer started")

    async def _create_case(self, event: dict) -> None:
        listing_id = UUID(event["listing_id"])
        seller_id = UUID(event["user_id"])
        source_event_id = event.get("event_id")
        documents = event.get("document_refs") or {}
        if not isinstance(documents, dict):
            raise ValueError("document_refs must be an object")
        document_refs = {
            name: value for name, value in documents.items()
            if name in PRIVATE_DOCUMENT_FIELDS and isinstance(value, str) and value
        }
        reports = event.get("analytics_reports") or {}
        if not isinstance(reports, dict):
            raise ValueError("analytics_reports must be an object")
        snapshot = event.get("listing_snapshot") or {}
        if not isinstance(snapshot, dict):
            raise ValueError("listing_snapshot must be an object")
        analytics_input = event.get("analytics_input")
        if isinstance(analytics_input, dict):
            snapshot = {**snapshot, "analytics_input": analytics_input}

        async with AsyncSessionLocal() as session:
            existing = await session.scalar(select(ModerationCase).where(
                ModerationCase.listing_id == listing_id
            ).with_for_update())
            if existing:
                return
            is_banned = await session.scalar(select(BlacklistEntry.id).where(
                BlacklistEntry.user_id == seller_id, BlacklistEntry.is_active.is_(True)
            ).limit(1))
            ai_report = reports.get("ai_report") or {}
            verification_level = (
                "deep"
                if SENSITIVE_DOCUMENT_FIELDS.intersection(document_refs)
                or event.get("verification_level") == "deep"
                or ai_report.get("verification_level") == "deep"
                else "basic"
            )
            case = ModerationCase(
                listing_id=listing_id,
                seller_id=seller_id,
                status="blocked" if is_banned else "pending",
                verification_level=verification_level,
                listing_snapshot=snapshot,
                analytics_reports=reports,
                document_refs=document_refs,
                source_event_id=source_event_id,
            )
            session.add(case)
            await session.flush()
            if is_banned:
                case.decision = "reject"
                case.decision_reason = "Аккаунт добавлен в чёрный список."
                case.decided_at = datetime.now(timezone.utc)
                self._queue_result(session, "moderation.listing.rejected", case, case.decision_reason)
            elif self._eligible_for_auto_release(snapshot, reports, document_refs):
                case.status = "auto_approved"
                case.decision = "approve"
                case.decided_at = datetime.now(timezone.utc)
                self._queue_result(session, "moderation.listing.approved", case)
            await session.commit()

    @staticmethod
    def _eligible_for_auto_release(snapshot: dict, reports: dict, document_refs: dict) -> bool:
        ai = reports.get("ai_report") or {}
        scripts = reports.get("scripts_report") or {}
        # Every private attachment needs a human to confirm what it proves and
        # that it belongs to this listing. Sensitive identity/financial files
        # additionally raise the verification level to deep.
        if document_refs:
            return False
        if ai.get("moderation_status") != "auto_ok":
            return False
        if ai.get("verification_level") != "basic" or ai.get("red_flag_rating") != "low":
            return False
        if ai.get("red_flags") or ai.get("moderation_reasons"):
            return False
        photos = ai.get("content_moderation")
        if not isinstance(photos, list) or not photos or not all(
            isinstance(item, dict) and item.get("status") == "allowed" for item in photos
        ):
            return False
        checks = scripts.get("consistency_report")
        if not isinstance(checks, list) or not all(
            isinstance(item, dict) and item.get("status") == "ok" for item in checks
        ):
            return False
        if snapshot.get("seller_status") == "ip":
            registry = ai.get("registry_match_report") or {}
            if registry.get("status") != "verified":
                return False
        return True

    @staticmethod
    def _queue_result(session, routing_key: str, case: ModerationCase, reason: str | None = None) -> None:
        payload = {
            "event": routing_key,
            "listing_id": str(case.listing_id),
            "user_id": str(case.seller_id),
            "verification_level": case.verification_level,
        }
        if reason:
            payload["user_safe_reason"] = reason
        session.add(ModerationOutboxEvent(routing_key=routing_key, payload=payload))

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


consumer = ModerationConsumer()

