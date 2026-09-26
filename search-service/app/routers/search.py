"""Для чего нужен этот файл:
Описывает HTTP-маршруты этой части API и связывает адреса и методы запросов с функциями-обработчиками.
"""

from fastapi import APIRouter, Query

from app.schemas.search import SearchResponse, SuggestResponse
from app.services.search_service import search_service

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    rooms: int | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    type: str | None = None,
    lat_min: float | None = None,
    lat_max: float | None = None,
    lng_min: float | None = None,
    lng_max: float | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SearchResponse:
    return await search_service.search(
        q=q,
        min_price=min_price,
        max_price=max_price,
        rooms=rooms,
        min_area=min_area,
        max_area=max_area,
        listing_type=type,
        lat_min=lat_min,
        lat_max=lat_max,
        lng_min=lng_min,
        lng_max=lng_max,
        page=page,
        page_size=page_size,
    )


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
) -> SuggestResponse:
    return await search_service.suggest(q, limit=limit)
