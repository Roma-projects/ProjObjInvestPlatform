"""Для чего нужен этот файл:
Получает сообщения из RabbitMQ и обрабатывает события других сервисов, не требуя прямого HTTP-вызова.
"""

import json
import logging
from datetime import date
from decimal import Decimal

import aio_pika
from aio_pika import ExchangeType

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.repositories.analytics_repo import AnalyticsRepository
from app.services.investment import compute_investment_score
from app.services.ml_service import ml_service
from app.services.pricing import estimate_rent

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalyticsConsumer:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None

    async def start(self) -> None:
        try:
            self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            channel = await self._connection.channel()
            await channel.set_qos(prefetch_count=10)
            exchange = await channel.declare_exchange(
                "listings_events", ExchangeType.TOPIC, durable=True
            )
            queue = await channel.declare_queue("analytics_queue", durable=True)
            await queue.bind(exchange, routing_key="listing.*")

            async def _on_message(message: aio_pika.IncomingMessage) -> None:
                async with message.process():
                    try:
                        body = json.loads(message.body.decode("utf-8"))
                        if body.get("event_type") != "listing.created":
                            return
                        await self._analyze(body)
                    except Exception as exc:
                        logger.exception("Analytics event failed: %s", exc)

            await queue.consume(_on_message)
            logger.info("Analytics consumer listening")
        except Exception as exc:
            logger.warning("Analytics consumer not started: %s", exc)

    async def _analyze(self, body: dict) -> None:
        listing_id = int(body["listing_id"])
        area = float(body.get("area", 40))
        rooms = int(body.get("rooms", 1))
        price = float(body.get("price", area * 150000))
        raw, _ = ml_service.predict_rent(area, rooms, None, price)
        rent = estimate_rent(
            area=area, rooms=rooms, floor=None, region="default", ml_estimate=raw
        )
        score, _, _, _ = compute_investment_score(
            price=price, area=area, rooms=rooms, rent_estimate=float(rent)
        )
        async with AsyncSessionLocal() as session:
            repo = AnalyticsRepository(session)
            await repo.save_analytics(
                listing_id=listing_id,
                rent_estimate=rent,
                investment_score=score,
                ml_model_version=settings.ml_model_version,
            )
            await repo.add_price_history(
                listing_id=listing_id,
                price=Decimal(str(price)),
                on_date=date.today(),
                source="listing.created",
            )
            await session.commit()
        logger.info("Auto-analyzed listing_id=%s rent=%s score=%s", listing_id, rent, score)

    async def stop(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()


consumer = AnalyticsConsumer()
