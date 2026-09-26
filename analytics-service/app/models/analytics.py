"""Для чего нужен этот файл:
Описывает таблицы базы данных и их поля. ORM преобразует эти модели Python в записи базы данных и обратно.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Float, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Analytics(Base):
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rent_estimate: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    investment_score: Mapped[float] = mapped_column(Float, nullable=False)
    ml_model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="estimate")
