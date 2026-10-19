"""Проверяет, что HTTP-запрос в Search пришёл из API Gateway."""

import hmac

from fastapi import HTTPException, Request, status

from app.config import get_settings

settings = get_settings()


async def require_gateway(request: Request) -> None:
    if not hmac.compare_digest(request.headers.get("X-Gateway-Token", ""), settings.gateway_shared_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Gateway required")
