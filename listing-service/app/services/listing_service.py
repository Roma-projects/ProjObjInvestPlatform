"""Для чего нужен этот файл:
Реализует правила создания, изменения, поиска и удаления объявлений. Сервисный слой связывает API, проверку данных и хранилище.
"""

import logging
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.rabbitmq.publisher import publisher
from app.repositories.listing_repo import ListingRepository
from app.schemas.listing import (
    ListingCreate,
    ListingListResponse,
    ListingResponse,
    ListingUpdate,
    PhotoResponse,
)
from app.services.geocoding import geocode_address
from app.utils.file_upload import save_upload

logger = logging.getLogger(__name__)


class ListingNotFound(Exception):
    pass


class ListingForbidden(Exception):
    pass


class ListingService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ListingRepository(session)

    def _to_response(self, listing: Listing) -> ListingResponse:
        return ListingResponse.model_validate(listing)

    async def create(self, owner_id: int, data: ListingCreate) -> ListingResponse:
        lat, lng = data.lat, data.lng
        if (lat is None or lng is None) and data.address:
            lat, lng = await geocode_address(data.address)

        listing = await self.repo.create(
            owner_id=owner_id,
            title=data.title,
            description=data.description,
            price=data.price,
            area=data.area,
            rooms=data.rooms,
            floor=data.floor,
            address=data.address,
            lat=lat,
            lng=lng,
            type=data.type.value,
            status=data.status.value,
        )
        await publisher.listing_created(listing)
        return self._to_response(listing)

    async def get(self, listing_id: int) -> ListingResponse:
        listing = await self.repo.get_by_id(listing_id)
        if not listing:
            raise ListingNotFound("Listing not found")
        return self._to_response(listing)

    async def list_listings(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        owner_id: int | None = None,
        listing_type: str | None = None,
        status: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        rooms: int | None = None,
    ) -> ListingListResponse:
        items, total = await self.repo.list(
            page=page,
            page_size=page_size,
            owner_id=owner_id,
            listing_type=listing_type,
            status=status,
            min_price=min_price,
            max_price=max_price,
            rooms=rooms,
        )
        return ListingListResponse(
            items=[self._to_response(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update(
        self, listing_id: int, owner_id: int, data: ListingUpdate
    ) -> ListingResponse:
        listing = await self.repo.get_by_id(listing_id)
        if not listing:
            raise ListingNotFound("Listing not found")
        if listing.owner_id != owner_id:
            raise ListingForbidden("Not the owner")

        payload = data.model_dump(exclude_unset=True)
        if "type" in payload and payload["type"] is not None:
            payload["type"] = payload["type"].value
        if "status" in payload and payload["status"] is not None:
            payload["status"] = payload["status"].value

        if "address" in payload and (
            "lat" not in payload or "lng" not in payload
        ):
            lat, lng = await geocode_address(payload["address"])
            payload.setdefault("lat", lat)
            payload.setdefault("lng", lng)

        listing = await self.repo.update(listing, **payload)
        await publisher.listing_updated(listing)
        return self._to_response(listing)

    async def delete(self, listing_id: int, owner_id: int) -> None:
        listing = await self.repo.get_by_id(listing_id)
        if not listing:
            raise ListingNotFound("Listing not found")
        if listing.owner_id != owner_id:
            raise ListingForbidden("Not the owner")
        lid, oid = listing.id, listing.owner_id
        await self.repo.delete(listing)
        await publisher.listing_deleted(lid, oid)

    async def add_photo(
        self,
        listing_id: int,
        owner_id: int,
        file: UploadFile,
        is_main: bool = False,
    ) -> PhotoResponse:
        listing = await self.repo.get_by_id(listing_id)
        if not listing:
            raise ListingNotFound("Listing not found")
        if listing.owner_id != owner_id:
            raise ListingForbidden("Not the owner")
        url = await save_upload(file, listing_id)
        photo = await self.repo.add_photo(listing_id, url, is_main=is_main)
        return PhotoResponse.model_validate(photo)
