"""Для чего нужен этот файл:
Описывает и проверяет формат данных API. Pydantic сверяет входящие запросы с этими схемами.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RentEstimateRequest(BaseModel):
    listing_id: int | None = None
    area: float = Field(..., gt=0)
    rooms: int = Field(..., ge=0)
    floor: int | None = None
    price: float | None = Field(default=None, ge=0)
    region: str = "default"
    lat: float | None = None
    lng: float | None = None
    type: str = "apartment"


class RentEstimateResponse(BaseModel):
    rent_estimate: Decimal
    currency: str = "RUB"
    model_version: str
    method: str


class InvestmentScoreRequest(BaseModel):
    listing_id: int | None = None
    price: float = Field(..., gt=0)
    area: float = Field(..., gt=0)
    rooms: int = Field(..., ge=0)
    rent_estimate: float | None = None
    region: str = "default"


class InvestmentScoreResponse(BaseModel):
    investment_score: float = Field(..., ge=0, le=100)
    annual_yield_pct: float
    risk_level: str
    commentary: str


class PriceHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    price: Decimal
    date: date
    source: str


class HistoryResponse(BaseModel):
    listing_id: int
    items: list[PriceHistoryItem]
    analytics: list["AnalyticsItem"] = []


class AnalyticsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    rent_estimate: Decimal
    investment_score: float
    ml_model_version: str
    created_at: datetime


class RetrainResponse(BaseModel):
    status: str
    model_version: str
    samples: int
