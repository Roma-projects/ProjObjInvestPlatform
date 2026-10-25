"""Для чего нужен этот файл:
Реализует правила регистрации, входа и выдачи учётных данных. Сервисный слой связывает API, проверку данных и хранилище.
"""

import logging

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis is not None:
            return self._redis
        try:
            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            return self._redis
        except Exception as exc:
            logger.warning("Redis unavailable, token blacklist disabled: %s", exc)
            return None

    async def register(self, data: RegisterRequest) -> UserResponse:
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise ConflictError("Email already registered")
        user = await self.repo.create(
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
        )
        return UserResponse.model_validate(user)

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("User is inactive")
        return TokenResponse(
            access_token=create_access_token(user.id, {"email": user.email}),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, data: RefreshRequest) -> TokenResponse:
        try:
            payload = decode_token(data.refresh_token)
        except ValueError as exc:
            raise AuthenticationError(str(exc)) from exc
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")

        redis = await self._get_redis()
        if redis is not None:
            blacklisted = await redis.get(f"blacklist:{data.refresh_token}")
            if blacklisted:
                raise AuthenticationError("Token has been revoked")

        user_id = int(payload["sub"])
        user = await self.repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        return TokenResponse(
            access_token=create_access_token(user.id, {"email": user.email}),
            refresh_token=create_refresh_token(user.id),
        )

    async def logout(self, refresh_token: str) -> None:
        redis = await self._get_redis()
        if redis is None:
            logger.info("Logout without Redis blacklist")
            return
        try:
            payload = decode_token(refresh_token)
            ttl = settings.refresh_token_expire_days * 24 * 3600
            await redis.setex(f"blacklist:{refresh_token}", ttl, "1")
            logger.info("Refresh token blacklisted for user=%s", payload.get("sub"))
        except ValueError:
            logger.warning("Logout with invalid token ignored")

    async def get_me(self, user_id: int) -> UserResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return UserResponse.model_validate(user)

    async def get_user_entity(self, user_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user
