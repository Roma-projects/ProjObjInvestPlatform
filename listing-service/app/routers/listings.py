"""Для чего нужен этот файл:
Описывает HTTP-маршруты этой части API и связывает адреса и методы запросов с функциями-обработчиками.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.dependencies import get_current_user_id, get_listing_service, require_gateway
from app.schemas.listing import (
    ListingCreate,
    ListingListResponse,
    ListingResponse,
    ListingUpdate,
    PhotoResponse,
)
from app.services.listing_service import (
    ListingForbidden,
    ListingNotFound,
    ListingService,
)

router = APIRouter(prefix="/api/v1/listings", tags=["listings"], dependencies=[Depends(require_gateway)])


@router.post("", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    body: ListingCreate,
    owner_id: int = Depends(get_current_user_id),
    service: ListingService = Depends(get_listing_service),
) -> ListingResponse:
    return await service.create(owner_id, body)


@router.get("", response_model=ListingListResponse)
async def list_listings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    owner_id: int | None = None,
    type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    rooms: int | None = None,
    service: ListingService = Depends(get_listing_service),
) -> ListingListResponse:
    return await service.list_listings(
        page=page,
        page_size=page_size,
        owner_id=owner_id,
        listing_type=type,
        status=status_filter,
        min_price=min_price,
        max_price=max_price,
        rooms=rooms,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: int,
    service: ListingService = Depends(get_listing_service),
) -> ListingResponse:
    try:
        return await service.get(listing_id)
    except ListingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: int,
    body: ListingUpdate,
    owner_id: int = Depends(get_current_user_id),
    service: ListingService = Depends(get_listing_service),
) -> ListingResponse:
    try:
        return await service.update(listing_id, owner_id, body)
    except ListingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ListingForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(
    listing_id: int,
    owner_id: int = Depends(get_current_user_id),
    service: ListingService = Depends(get_listing_service),
) -> None:
    try:
        await service.delete(listing_id, owner_id)
    except ListingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ListingForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post(
    "/{listing_id}/photos",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photo(
    listing_id: int,
    file: UploadFile = File(...),
    is_main: bool = Form(False),
    owner_id: int = Depends(get_current_user_id),
    service: ListingService = Depends(get_listing_service),
) -> PhotoResponse:
    try:
        return await service.add_photo(listing_id, owner_id, file, is_main=is_main)
    except ListingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ListingForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
