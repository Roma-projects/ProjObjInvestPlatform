"""Для чего нужен этот файл:
Содержит функции для создания и проверки JWT-токенов, с помощью которых сервер проверяет личность пользователя в запросах.
"""

"""JWT helpers: access (15m) + refresh (7d)."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from shared.config import get_shared_settings


def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_shared_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload, settings.jwt_private_key, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_shared_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload, settings.jwt_private_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_shared_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
