"""Для чего нужен этот файл:
Собирает операции чтения и записи в базе данных, отделяя запросы к хранилищу от правил приложения.
"""

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.listing import Listing, Photo

logger = logging.getLogger(__name__)


class ListingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, listing_id: int) -> Listing | None:
        result = await self.session.execute(
            select(Listing)
            .options(selectinload(Listing.photos))
            .where(Listing.id == listing_id)
        )
        return result.scalar_one_or_none()

    async def list(
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
    ) -> tuple[list[Listing], int]:
        query = select(Listing).options(selectinload(Listing.photos))
        count_query = select(func.count(Listing.id))

        if owner_id is not None:
            query = query.where(Listing.owner_id == owner_id)
            count_query = count_query.where(Listing.owner_id == owner_id)
        if listing_type:
            query = query.where(Listing.type == listing_type)
            count_query = count_query.where(Listing.type == listing_type)
        if status:
            query = query.where(Listing.status == status)
            count_query = count_query.where(Listing.status == status)
        if min_price is not None:
            query = query.where(Listing.price >= min_price)
            count_query = count_query.where(Listing.price >= min_price)
        if max_price is not None:
            query = query.where(Listing.price <= max_price)
            count_query = count_query.where(Listing.price <= max_price)
        if rooms is not None:
            query = query.where(Listing.rooms == rooms)
            count_query = count_query.where(Listing.rooms == rooms)

        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(
            query.order_by(Listing.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), int(total)

    async def create(self, **kwargs) -> Listing:
        listing = Listing(**kwargs)
        self.session.add(listing)
        await self.session.flush()
        await self.session.refresh(listing, attribute_names=["photos"])
        return listing

    async def update(self, listing: Listing, **kwargs) -> Listing:
        for key, value in kwargs.items():
            if value is not None:
                setattr(listing, key, value)
        await self.session.flush()
        await self.session.refresh(listing, attribute_names=["photos"])
        return listing

    async def delete(self, listing: Listing) -> None:
        await self.session.delete(listing)

    async def add_photo(
        self, listing_id: int, url: str, is_main: bool = False
    ) -> Photo:
        if is_main:
            existing = await self.session.execute(
                select(Photo).where(Photo.listing_id == listing_id)
            )
            for photo in existing.scalars().all():
                photo.is_main = False
        photo = Photo(listing_id=listing_id, url=url, is_main=is_main)
        self.session.add(photo)
        await self.session.flush()
        await self.session.refresh(photo)
        return photo
