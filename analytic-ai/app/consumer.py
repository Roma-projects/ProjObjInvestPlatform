"""Принимает события объявления, приостанавливает задачу и возобновляет её с реестром."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import aio_pika
import redis.asyncio as redis
from aio_pika import ExchangeType
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.model_client import VisionAnalyzer
from app.models import ModelConfig

logger = logging.getLogger(__name__)
settings = get_settings()


class AIConsumer:
    """Координирует очереди started, reply и timeout, чтобы не блокировать другие задачи."""

    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.Channel | None = None
        self.redis: redis.Redis | None = None
        self.analyzer = VisionAnalyzer()
        self.exchange: aio_pika.Exchange | None = None
        self._photo_tasks: dict[str, asyncio.Task[dict]] = {}

    async def start(self) -> None:
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        self.exchange = await self.channel.declare_exchange("listings", ExchangeType.TOPIC, durable=True)
        incoming = await self.channel.declare_queue(
            "analytic.ai", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "analytic.ai.dlq"},
        )
        await self.channel.declare_queue("analytic.ai.dlq", durable=True)
        await incoming.bind(self.exchange, routing_key="listing.creation.started")
        await self.channel.declare_queue("ai.resume.dlq", durable=True)
        resume = await self.channel.declare_queue(
            "ai.resume", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "ai.resume.dlq"},
        )
        await resume.consume(self._on_resume)
        await incoming.consume(self._on_started)
        await self._save_model_config()

    async def _save_model_config(self) -> None:
        """Сохраняет версию модели и промпт; секрет API key в таблицу не попадает."""
        async with SessionLocal() as session:
            row = await session.scalar(select(ModelConfig).where(ModelConfig.id == 1))
            if row is None:
                session.add(ModelConfig(id=1, model_name=self.analyzer.model_name,
                                        policy_version="tender-v1", endpoint_host=self.analyzer.endpoint_host(),
                                        system_prompt="Four tasks only; no marketing copy; redact confidential fields."))
            else:
                row.model_name = self.analyzer.model_name
                row.endpoint_host = self.analyzer.endpoint_host()
                row.updated_at = datetime.now(timezone.utc)
            await session.commit()

    async def _on_started(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=False):
            event = json.loads(message.body.decode())
            correlation_id = str(event.get("correlation_id", ""))
            if not correlation_id or not await self.redis.set(f"ai:started:{correlation_id}", "1", ex=600, nx=True):
                return
            data = event.get("data_for_analytics") or {}
            if data.get("registry_check") == "awaiting":
                self._photo_tasks[correlation_id] = asyncio.create_task(
                    self.analyzer.analyze_while_registry_pending(data)
                )
                await self._suspend(event)
            else:
                await self._analyze_and_publish(event, data, None)

    async def _suspend(self, event: dict) -> None:
        correlation_id = str(event["correlation_id"])
        reply_name = f"ai.reply.{correlation_id}"
        assert self.channel is not None
        reply_queue = await self.channel.declare_queue(reply_name, durable=True, arguments={"x-expires": 300000})
        await self.redis.setex(f"ai:pending:{correlation_id}", 600, json.dumps(event, ensure_ascii=False))
        timeout_seconds = 120
        timer_name = f"ai.timeout.{correlation_id}"
        timer_queue = await self.channel.declare_queue(
            timer_name, durable=True,
            arguments={"x-message-ttl": timeout_seconds * 1000, "x-dead-letter-exchange": "",
                       "x-dead-letter-routing-key": "ai.resume", "x-expires": (timeout_seconds + 300) * 1000},
        )
        await self.channel.default_exchange.publish(
            aio_pika.Message(json.dumps({"correlation_id": correlation_id, "kind": "timeout"}).encode(),
                             delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=timer_name,
        )

        async def handle_reply(message: aio_pika.IncomingMessage) -> None:
            async with message.process(requeue=False):
                event_json = await self.redis.get(f"ai:pending:{correlation_id}")
                if event_json:
                    await self.redis.delete(f"ai:pending:{correlation_id}")
                    await self.channel.queue_delete(timer_name, if_unused=False, if_empty=False)
                    event = json.loads(event_json)
                    registry_payload = json.loads(message.body.decode())
                    data = event.get("data_for_analytics") or {}
                    data["registry_check"] = registry_payload.get("status", "error")
                    await self._analyze_and_publish(
                        event, data, registry_payload.get("registry_extract"), reuse_photo_task=True
                    )
                await self.channel.queue_delete(reply_name, if_unused=False, if_empty=False)

        await reply_queue.consume(handle_reply)

    async def _on_resume(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=False):
            timer = json.loads(message.body.decode())
            correlation_id = str(timer.get("correlation_id", ""))
            event_json = await self.redis.get(f"ai:pending:{correlation_id}")
            if not event_json:
                return
            await self.redis.delete(f"ai:pending:{correlation_id}")
            event = json.loads(event_json)
            data = event.get("data_for_analytics") or {}
            data["registry_check"] = "timeout"
            await self._analyze_and_publish(event, data, None, reuse_photo_task=True)

    async def _consume_photo_task(self, correlation_id: str) -> dict | None:
        task = self._photo_tasks.pop(correlation_id, None)
        if task is None:
            return None
        try:
            return await task
        except Exception:
            logger.exception("Parallel photo analysis failed for correlation %s", correlation_id)
            return None

    async def _analyze_and_publish(
        self, event: dict, data: dict, registry: dict | None, *, reuse_photo_task: bool = False
    ) -> None:
        correlation_id = str(event["correlation_id"])
        complete_key = f"ai:complete:{correlation_id}"
        if not await self.redis.set(complete_key, "1", ex=86400, nx=True):
            task = self._photo_tasks.pop(correlation_id, None)
            if task and not task.done():
                task.cancel()
            return
        try:
            photo_report = await self._consume_photo_task(correlation_id) if reuse_photo_task else None
            if photo_report is not None:
                report = self.analyzer.recalculate_with_registry(photo_report, data, registry)
            else:
                report = await self.analyzer.analyze(data, registry)
            # Registry verification is deterministic; an LLM must not approve an unmatched seller.
            if data.get("seller_status") == "ip" and data.get("registry_check") not in {"timeout", "error"}:
                identity = (registry or {}).get("identity_check") or {}
                verified = bool(identity.get("verified"))
                report["registry_match_report"] = {
                    "status": "verified" if verified else "unverified",
                    "identity_check": identity,
                    "document_downloaded": bool(identity.get("document_downloaded")),
                }
                if not verified:
                    report["moderation_status"] = "requires_moderation"
                    reasons = report.setdefault("moderation_reasons", [])
                    reasons.append("registry_identity_unverified")
                    moderator = report.setdefault("moderator_report", {})
                    moderator["review_required"] = True
                    moderator["registry_identity_check"] = identity
            result = {
                "event": "listing.ai.analysis.completed",
                "event_id": f"{correlation_id}:ai",
                "correlation_id": correlation_id,
                "listing_id": event["listing_id"],
                "user_id": event["user_id"],
                **report,
            }
            assert self.exchange is not None
            await self.exchange.publish(aio_pika.Message(
                json.dumps(result, ensure_ascii=False).encode(), content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT, message_id=result["event_id"],
            ), routing_key="listing.ai.analysis.completed", mandatory=True)
        except Exception:
            await self.redis.delete(complete_key)
            logger.exception("AI analysis failed for listing %s", event.get("listing_id"))
            raise

    async def stop(self) -> None:
        await self.analyzer.close()
        if self.redis:
            await self.redis.aclose()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
