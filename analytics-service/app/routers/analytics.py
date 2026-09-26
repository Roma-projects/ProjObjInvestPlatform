"""Для чего нужен этот файл:
Описывает HTTP-маршруты этой части API и связывает адреса и методы запросов с функциями-обработчиками.
"""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.repositories.analytics_repo import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsItem,
    HistoryResponse,
    InvestmentScoreRequest,
    InvestmentScoreResponse,
    PriceHistoryItem,
    RentEstimateRequest,
    RentEstimateResponse,
    RetrainResponse,
)
from app.services.investment import compute_investment_score
from app.services.ml_service import ml_service
from app.services.pricing import estimate_rent

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
settings = get_settings()


@router.post("/rent-estimate", response_model=RentEstimateResponse)
async def rent_estimate(
    body: RentEstimateRequest,
    session: AsyncSession = Depends(get_db),
) -> RentEstimateResponse:
    raw, method = ml_service.predict_rent(body.area, body.rooms, body.floor, body.price)
    rent = estimate_rent(
        area=body.area,
        rooms=body.rooms,
        floor=body.floor,
        region=body.region,
        ml_estimate=raw,
    )
    if body.listing_id is not None:
        repo = AnalyticsRepository(session)
        score, _, _, _ = compute_investment_score(
            price=body.price or float(rent) * 200,
            area=body.area,
            rooms=body.rooms,
            rent_estimate=float(rent),
        )
        await repo.save_analytics(
            listing_id=body.listing_id,
            rent_estimate=rent,
            investment_score=score,
            ml_model_version=settings.ml_model_version,
        )
    return RentEstimateResponse(
        rent_estimate=rent,
        model_version=settings.ml_model_version,
        method=method,
    )


@router.post("/investment-score", response_model=InvestmentScoreResponse)
async def investment_score(body: InvestmentScoreRequest) -> InvestmentScoreResponse:
    rent = body.rent_estimate
    if rent is None:
        raw, _ = ml_service.predict_rent(body.area, body.rooms, None, body.price)
        rent = float(
            estimate_rent(
                area=body.area,
                rooms=body.rooms,
                floor=None,
                region=body.region,
                ml_estimate=raw,
            )
        )
    score, yld, risk, commentary = compute_investment_score(
        price=body.price,
        area=body.area,
        rooms=body.rooms,
        rent_estimate=rent,
    )
    return InvestmentScoreResponse(
        investment_score=score,
        annual_yield_pct=yld,
        risk_level=risk,
        commentary=commentary,
    )


@router.get("/history/{listing_id}", response_model=HistoryResponse)
async def history(
    listing_id: int,
    session: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    repo = AnalyticsRepository(session)
    items = await repo.history(listing_id)
    analytics = await repo.analytics_for_listing(listing_id)
    # Seed synthetic history if empty (MVP demo)
    if not items:
        base = Decimal("5000000")
        today = date.today()
        for i in range(5, 0, -1):
            await repo.add_price_history(
                listing_id=listing_id,
                price=base * Decimal(str(1 - i * 0.03)),
                on_date=today - timedelta(days=365 * i),
                source="synthetic",
            )
        items = await repo.history(listing_id)
    return HistoryResponse(
        listing_id=listing_id,
        items=[PriceHistoryItem.model_validate(i) for i in items],
        analytics=[AnalyticsItem.model_validate(a) for a in analytics],
    )


@router.post("/retrain", response_model=RetrainResponse)
async def retrain() -> RetrainResponse:
    samples = ml_service.retrain_synthetic()
    return RetrainResponse(
        status="ok",
        model_version=settings.ml_model_version,
        samples=samples,
    )
