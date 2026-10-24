"""Отправляет реестровый запрос в Parsers по RabbitMQ и затем передаёт ответ в Analytic AI."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

import aio_pika
from dotenv import load_dotenv

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parents[1]
AI_DIR = PROJECT_ROOT / "analytic-ai"


async def run(input_path: Path, output_path: Path, timeout: int) -> dict[str, Any]:
    """Сначала ждёт реальный ответ Parsers, потом формирует ответ AI из полученных данных."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    load_dotenv(AI_DIR / ".env", override=False)
    if not os.getenv("POLZA_API_KEY") and not os.getenv("QWEN_API_KEY"):
        raise SystemExit("AI ключ не задан: заполните analytic-ai/.env либо переменные окружения.")
    sys.path.insert(0, str(AI_DIR))
    from app.model_client import VisionAnalyzer  # noqa: PLC0415

    fixture = json.loads(input_path.read_text(encoding="utf-8"))
    request = dict(fixture["parser_request"])
    correlation_id = f"{request['correlation_id']}-{uuid4().hex[:8]}"
    request["correlation_id"] = correlation_id
    request["reply_to"] = f"ai.reply.{correlation_id}"
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()
    try:
        reply_queue = await channel.declare_queue(request["reply_to"], durable=True,
                                                  arguments={"x-expires": (timeout + 60) * 1000})
        exchange = await channel.declare_exchange("parsers", aio_pika.ExchangeType.TOPIC, durable=True)
        await exchange.publish(
            aio_pika.Message(json.dumps(request, ensure_ascii=False).encode(),
                             content_type="application/json", delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                             correlation_id=correlation_id),
            routing_key="parsers.request.registry", mandatory=True,
        )
        print(f"Запрос Parsers опубликован: correlation_id={correlation_id}; жду до {timeout} сек.")
        message = await asyncio.wait_for(reply_queue.get(fail=False), timeout=timeout)
        if message is None:
            raise TimeoutError("Parsers не ответил до истечения таймаута.")
        async with message.process(requeue=False):
            parser_result = json.loads(message.body.decode("utf-8"))
    finally:
        await connection.close()

    data = dict(fixture["data_for_analytics"])
    data["registry_check"] = parser_result.get("status", "error")
    analyzer = VisionAnalyzer()
    try:
        report = await analyzer.analyze(data, parser_result.get("registry_extract"))
    finally:
        await analyzer.close()

    identity = (parser_result.get("registry_extract") or {}).get("identity_check") or {}
    # Same deterministic fail-closed rule as the production AI consumer.
    verified = bool(identity.get("verified"))
    report["registry_match_report"] = {
        "status": "verified" if verified else "unverified",
        "identity_check": identity,
        "document_downloaded": bool(identity.get("document_downloaded")),
    }
    if not verified:
        report["moderation_status"] = "requires_moderation"
        report.setdefault("moderation_reasons", []).append("registry_identity_unverified")
        report.setdefault("moderator_report", {})["review_required"] = True
    result = {
        "event": "listing.ai.analysis.completed",
        "event_id": f"{correlation_id}:ai",
        "correlation_id": correlation_id,
        "listing_id": request["listing_id"],
        "parser_result": parser_result,
        "identity_check": identity,
        "identity_verified": verified,
        "analytics_result": report,
    }
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Parsers: {parser_result.get('status')}; скачан документ: {bool(identity.get('document_downloaded'))}; "
          f"сверка ИП: {'успешна' if verified else 'не подтверждена'}")
    print(f"Analytic AI: {report.get('moderation_status')}; JSON: {output_path}")
    return result


def main() -> None:
    """Принимает пути к JSON и таймауту, не выводя секреты окружения."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=TEST_DIR / "registry_then_ai.json")
    parser.add_argument("--output", type=Path, default=TEST_DIR / "registry_then_ai_result.json")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    asyncio.run(run(args.input, args.output, args.timeout))


if __name__ == "__main__":
    main()
