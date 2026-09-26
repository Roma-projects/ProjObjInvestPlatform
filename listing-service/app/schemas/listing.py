"""Для чего нужен этот файл:
Описывает и проверяет формат данных API. Pydantic сверяет входящие запросы с этими схемами.
"""

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


class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    url: str
    is_main: bool = False


class ListingCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    price: Decimal = Field(..., ge=0)
    area: float = Field(..., gt=0)
    rooms: int = Field(..., ge=0)
    floor: int | None = None
    address: str = Field(..., min_length=3)
    lat: float | None = None
    lng: float | None = None
    type: ListingType = ListingType.APARTMENT
    status: ListingStatus = ListingStatus.ACTIVE


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    area: float | None = Field(default=None, gt=0)
    rooms: int | None = Field(default=None, ge=0)
    floor: int | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    type: ListingType | None = None
    status: ListingStatus | None = None


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    title: str
    description: str | None
    price: Decimal
    area: float
    rooms: int
    floor: int | None
    address: str
    lat: float | None
    lng: float | None
    type: str
    status: str
    created_at: datetime
    updated_at: datetime
    photos: list[PhotoResponse] = []


class ListingListResponse(BaseModel):
    items: list[ListingResponse]
    total: int
    page: int
    page_size: int
