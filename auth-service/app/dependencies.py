"""Для чего нужен этот файл:
Содержит повторно используемые зависимости FastAPI, например получение текущего пользователя или сессии базы данных.
"""

import hmac

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AuthenticationError
from app.models.user import User
from app.security import decode_token
from app.services.auth_service import AuthService
from app.config import get_settings

settings = get_settings()

bearer_scheme = HTTPBearer(auto_error=False)


async def require_gateway(request: Request) -> None:
    supplied = request.headers.get("X-Gateway-Token", "")
    if not hmac.compare_digest(supplied, settings.gateway_shared_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Gateway required")


async def get_auth_service(
    session: AsyncSession = Depends(get_db),
) -> AuthService:
    return AuthService(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Missing bearer token")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")
    user_id = int(payload["sub"])
    return await auth_service.get_user_entity(user_id)


async def get_request_id(request: Request) -> str | None:
    return request.headers.get("X-Request-ID")
