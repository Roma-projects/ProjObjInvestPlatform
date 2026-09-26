"""Для чего нужен этот файл:
Содержит повторно используемые зависимости FastAPI, например получение текущего пользователя или сессии базы данных.
"""

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.services.listing_service import ListingService

bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()


async def get_listing_service(
    session: AsyncSession = Depends(get_db),
) -> ListingService:
    return ListingService(session)


def _decode_access(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )
    return payload


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    payload = _decode_access(credentials.credentials)
    return int(payload["sub"])


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int | None:
    if credentials is None:
        return None
    try:
        payload = _decode_access(credentials.credentials)
        return int(payload["sub"])
    except HTTPException:
        return None
