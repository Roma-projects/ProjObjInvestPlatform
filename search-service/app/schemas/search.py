"""Для чего нужен этот файл:
Описывает и проверяет формат данных API. Pydantic сверяет входящие запросы с этими схемами.
"""

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    listing_id: int
    title: str
    price: float
    area: float
    rooms: int
    address: str
    lat: float | None = None
    lng: float | None = None
    type: str = "apartment"
    status: str = "active"
    score: float = 0.0


class SearchResponse(BaseModel):
    items: list[SearchHit]
    total: int
    query: str | None = None
    cached: bool = False


class SuggestItem(BaseModel):
    text: str
    listing_id: int | None = None


class SuggestResponse(BaseModel):
    suggestions: list[SuggestItem] = Field(default_factory=list)
