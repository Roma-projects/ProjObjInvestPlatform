"""Для чего нужен этот файл:
Описывает HTTP-маршруты этой части API и связывает адреса и методы запросов с функциями-обработчиками.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import require_gateway
from app.schemas.search import (
    CatalogQueryRequest,
    CatalogMapRequest,
    SearchResponse,
    SuggestRequest,
    SuggestResponse,
)
from app.services.search_service import search_service

router = APIRouter(prefix="/api/v1/search", tags=["search"], dependencies=[Depends(require_gateway)])


@router.get("/catalog")
async def search_catalog(
    q: str | None = Query(None, max_length=120),
    business_type: str | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    verification_status: str | None = Query(None, pattern="^(all|basic|deep)$"),
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc)$"),
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Return public business cards; the cursor keeps page boundaries stable."""
    return await search_service.search_businesses(
        q=q, business_type=business_type, min_price=min_price, max_price=max_price,
        verification_status=verification_status, sort=sort, cursor=cursor, limit=limit,
    )


@router.post("/catalog/query")
async def search_catalog_json(body: CatalogQueryRequest) -> dict:
    """Filter public businesses from a JSON body so browser filters need no query string."""
    return await search_service.search_businesses(
        q=body.q,
        business_type=body.business_type,
        min_price=body.min_price,
        max_price=body.max_price,
        verification_status=None if body.verification_status == "all" else body.verification_status,
        sort=body.sort,
        cursor=body.cursor,
        limit=body.limit,
        deal_composition=body.deal_composition,
        property_type=body.property_type,
        property_condition=body.property_condition,
        transfer_method=body.transfer_method,
        revenue_trend=body.revenue_trend,
        city=body.city,
    )


@router.post("/catalog/map")
async def catalog_map_json(body: CatalogMapRequest) -> dict:
    """Return coordinates and titles for published listings using a JSON body."""
    return await search_service.map_businesses(body.model_dump(exclude_none=True))


@router.get("/catalog/{listing_id}")
async def get_catalog_business(listing_id: str) -> dict:
    item = await search_service.get_business(listing_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Published listing not found")
    return item


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


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_json(body: SuggestRequest) -> SuggestResponse:
    """JSON variant for search suggestions; keeps search terms out of the URL."""
    return await search_service.suggest(body.q, limit=body.limit)
