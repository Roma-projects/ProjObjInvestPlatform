"""Для чего нужен этот файл:
Содержит повторно используемые зависимости FastAPI, например получение текущего пользователя или сессии базы данных.
"""

import hmac
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()


async def require_gateway(request: Request) -> None:
    """Reject requests that did not come through the authenticated API Gateway."""
    supplied = request.headers.get("X-Gateway-Token", "")
    if not hmac.compare_digest(supplied, settings.gateway_shared_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Gateway required")


async def get_current_user_uuid(request: Request) -> UUID:
    """Read the authenticated UUID injected by Gateway after its JWT checks."""
    user_id = request.headers.get("X-Authenticated-User-ID", "")
    try:
        return UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gateway user identity is invalid") from exc


