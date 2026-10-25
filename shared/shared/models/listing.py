"""Для чего нужен этот файл:
Описывает таблицы базы данных и их поля. ORM преобразует эти модели Python в записи базы данных и обратно.
"""

"""Shared Listing DTO (not a SQLAlchemy model)."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ListingType(str, Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    ROOM = "room"
    COMMERCIAL = "commercial"
    LAND = "land"


class ListingStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    RENTED = "rented"


class ListingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    owner_id: int
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    price: Decimal = Field(..., ge=0)
    area: float = Field(..., gt=0)
    rooms: int = Field(..., ge=0)
    floor: int | None = None
    address: str
    lat: float | None = None
    lng: float | None = None
    type: ListingType = ListingType.APARTMENT
    status: ListingStatus = ListingStatus.ACTIVE
    created_at: datetime | None = None
    updated_at: datetime | None = None
