"""Для чего нужен этот файл:
Собирает операции чтения и записи в базе данных, отделяя запросы к хранилищу от правил приложения.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import Analytics, PriceHistory


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_analytics(
        self,
        *,
        listing_id: int,
        rent_estimate: Decimal,
        investment_score: float,
        ml_model_version: str,
    ) -> Analytics:
        row = Analytics(
            listing_id=listing_id,
            rent_estimate=rent_estimate,
            investment_score=investment_score,
            ml_model_version=ml_model_version,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def add_price_history(
        self,
        *,
        listing_id: int,
        price: Decimal,
        on_date: date,
        source: str = "estimate",
    ) -> PriceHistory:
        row = PriceHistory(
            listing_id=listing_id, price=price, date=on_date, source=source
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def history(self, listing_id: int) -> list[PriceHistory]:
        result = await self.session.execute(
            select(PriceHistory)
            .where(PriceHistory.listing_id == listing_id)
            .order_by(PriceHistory.date.asc())
        )
        return list(result.scalars().all())

    async def analytics_for_listing(self, listing_id: int) -> list[Analytics]:
        result = await self.session.execute(
            select(Analytics)
            .where(Analytics.listing_id == listing_id)
            .order_by(Analytics.created_at.desc())
        )
        return list(result.scalars().all())
