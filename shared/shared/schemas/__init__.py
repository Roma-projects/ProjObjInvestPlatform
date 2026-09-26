"""Для чего нужен этот файл:
Описывает и проверяет формат данных API. Pydantic сверяет входящие запросы с этими схемами.
"""

from shared.schemas.user import (
    TokenPair,
    TokenRefresh,
    UserCreate,
    UserLogin,
    UserResponse,
)
from shared.schemas.listing import (
    ListingCreate,
    ListingResponse,
    ListingUpdate,
    PhotoResponse,
)

__all__ = [
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenPair",
    "TokenRefresh",
    "ListingCreate",
    "ListingUpdate",
    "ListingResponse",
    "PhotoResponse",
]
