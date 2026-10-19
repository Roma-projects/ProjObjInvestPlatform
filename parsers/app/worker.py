"""Обрабатывает одну задачу реестров, сохраняет результат и отвечает только в reply_to."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import aio_pika

from app.models import ParserRequest, ParserResponse
from app.parsers import EgrulParser, FedresursParser, KadParser, PbParser
from app.storage import LocalStorage, MongoStorage

logger = logging.getLogger(__name__)


class ParserWorker:
    """Координирует источники последовательно и изолирует сбой одного источника."""

    def __init__(self, storage: MongoStorage) -> None:
        self.storage = storage
        self.parsers = {item.source: item for item in
                        (EgrulParser(), PbParser(), FedresursParser(), KadParser())}

    async def process(self, request: ParserRequest) -> ParserResponse:
        started = time.monotonic()
        listing_files = LocalStorage(request.listing_id)
        await self.storage.tasks.update_one(
            {"correlation_id": request.correlation_id},
            {"$setOnInsert": {"correlation_id": request.correlation_id,
                               "listing_id": request.listing_id, "inn": request.inn,
                               "fio": request.fio, "status": request.status,
                               "ogrnip": request.ogrnip, "state": "pending",
                               "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        await self.storage.tasks.update_one(
            {"correlation_id": request.correlation_id}, {"$set": {"state": "processing"}}
        )
        source_results: dict[str, dict[str, Any]] = {}
        failed: list[str] = []
        files: dict[str, list[str]] = {}
        try:
            async with asyncio.timeout(request.ttl_seconds):
                for source in request.sources:
                    try:
                        parser = self.parsers[source]
                        source_results[source] = await parser.run(
                            inn=request.inn, ogrnip=request.ogrnip, fio=request.fio,
                            storage=listing_files, mongo=self.storage,
                        )
                        files[source] = source_results[source]["files"]
                    except Exception as exc:
                        logger.warning("Registry source %s failed (%s)", source, type(exc).__name__)
                        failed.append(source)
        except TimeoutError:
            failed.extend(source for source in request.sources if source not in source_results and source not in failed)

        text = " ".join(result.get("extract", {}).get("source_text_excerpt") or ""
                         for result in source_results.values())
        registry = self._extract_fields(text, request.fio, request.ogrnip)
        if failed:
            result_status = "partial" if source_results else "error"
        else:
            result_status = "ok" if text else "not_found"
        response = ParserResponse(
            correlation_id=request.correlation_id,
            listing_id=request.listing_id,
            status=result_status,
            registry_extract=registry,
            files=files,
            metadata={
                "sources_checked": request.sources,
                "failed_sources": failed,
                "total_duration_ms": int((time.monotonic() - started) * 1000),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        await self.storage.extracted.update_one(
            {"listing_id": request.listing_id},
            {"$set": {"listing_id": request.listing_id, "inn": request.inn,
                       "fio": request.fio, "extract": registry, "files": files,
                       "metadata": response.metadata, "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        await self.storage.tasks.update_one(
            {"correlation_id": request.correlation_id},
            {"$set": {"state": "completed" if result_status in {"ok", "not_found", "partial"} else "failed",
                       "completed_at": datetime.now(timezone.utc), "result_status": result_status,
                       "error_message": "One or more sources failed" if failed else None}},
        )
        return response

    @staticmethod
    def _extract_fields(text: str, expected_fio: str, expected_ogrnip: str | None) -> dict[str, Any]:
        """Extracts conservative text hints; the AI receives null when a value is uncertain."""
        ogrnip_match = re.search(r"(?<!\d)(\d{15})(?!\d)", text)
        date_match = re.search(r"(?<!\d)(\d{2}\.\d{2}\.\d{4})(?!\d)", text)
        okved = list(dict.fromkeys(re.findall(r"(?<!\d)(\d{2}(?:\.\d{1,2}){1,2})(?!\d)", text)))
        status = "действующая" if re.search(r"действующ", text, re.IGNORECASE) else None
        region_match = re.search(r"регион\s*[:\-]\s*([^,;]{2,80})", text, re.IGNORECASE)
        return {
            "fio": expected_fio if expected_fio.casefold() in text.casefold() else None,
            "ogrnip": ogrnip_match.group(1) if ogrnip_match else None,
            "registration_date": date_match.group(1) if date_match else None,
            "okved": okved,
            "status": status,
            "region": region_match.group(1).strip() if region_match else None,
            "tax_system": None, "employee_count": None, "annual_revenue": None,
            "risk_factors": [], "bankruptcy_proceedings": bool(re.search(r"банкрот", text, re.IGNORECASE)),
            "arbitration_cases": [],
            "expected_ogrnip_match": (ogrnip_match.group(1) == expected_ogrnip) if ogrnip_match and expected_ogrnip else None,
        }


class ParserQueueConsumer:
    """Читает RabbitMQ задания и публикует ответы напрямую в указанную reply queue."""

    def __init__(self, storage: MongoStorage) -> None:
        self.storage = storage
        self.worker = ParserWorker(storage)
        self.connection: aio_pika.RobustConnection | None = None

    async def start(self, rabbitmq_url: str) -> None:
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await self.connection.channel()
        await channel.set_qos(prefetch_count=5)
        exchange = await channel.declare_exchange("parsers", aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(
            "parsers.tasks", durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "parsers.tasks.dlq"},
        )
        await channel.declare_queue("parsers.tasks.dlq", durable=True)
        await queue.bind(exchange, routing_key="parsers.request.registry")

        async def handle(message: aio_pika.IncomingMessage) -> None:
            async with message.process(requeue=False):
                data = json.loads(message.body.decode("utf-8"))
                request = ParserRequest.model_validate(data)
                if not request.reply_to.startswith("ai.reply."):
                    raise ValueError("reply_to must identify an AI resume queue")
                response = await self.worker.process(request)
                await self.connection.default_exchange.publish(
                    aio_pika.Message(
                        response.model_dump_json().encode(), content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        message_id=request.correlation_id,
                        correlation_id=request.correlation_id,
                    ), routing_key=request.reply_to, mandatory=True,
                )
        await queue.consume(handle)

    async def stop(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
