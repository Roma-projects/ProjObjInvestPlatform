"""Для чего нужен этот файл:
Описывает и проверяет формат данных API. Pydantic сверяет входящие запросы с этими схемами.
"""

from pydantic import BaseModel, Field, model_validator


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


class CatalogQueryRequest(BaseModel):
    """JSON filter contract used by browser clients instead of query strings."""

    q: str | None = Field(default=None, max_length=120)
    business_type: str | list[str] | None = None
    deal_composition: str | list[str] | None = None
    property_type: str | list[str] | None = None
    property_condition: str | list[str] | None = None
    transfer_method: str | list[str] | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    verification_status: str | None = Field(default=None, pattern=r"^(all|basic|deep)$")
    revenue_trend: str | list[str] | None = None
    city: str | None = Field(default=None, max_length=100)
    sort: str = Field(default="newest", pattern=r"^(newest|price_asc|price_desc)$")
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_price_range(self):
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price must be less than or equal to max_price")
        return self


class CatalogMapRequest(BaseModel):
    """JSON filters for public map markers; map requests intentionally have no URL params."""

    q: str | None = Field(default=None, max_length=120)
    business_type: str | list[str] | None = None
    deal_composition: str | list[str] | None = None
    property_type: str | list[str] | None = None
    property_condition: str | list[str] | None = None
    transfer_method: str | list[str] | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    verification_status: str | None = Field(default=None, pattern=r"^(all|basic|deep)$")
    revenue_trend: str | list[str] | None = None
    city: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_price_range(self):
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price must be less than or equal to max_price")
        return self


class SuggestRequest(BaseModel):
    q: str = Field(min_length=1, max_length=120)
    limit: int = Field(default=10, ge=1, le=50)
