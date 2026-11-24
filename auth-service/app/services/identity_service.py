"""Реализация новых Auth-сценариев: верификация, сессии и профиль."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.email_sender import EmailRateLimitError, EmailSender
from app.models.session import AuthSession
from app.models.user import User
from app.rabbitmq.publisher import publisher
from app.schemas.identity import DeviceInfo, ProfilePatch, RegisterBody
from app.security import create_access_token, create_refresh_token, hash_password, verify_password

settings = get_settings()

_CONSUME_VERIFICATION_SCRIPT = """
local attempts = tonumber(redis.call('GET', KEYS[1]) or '0')
if attempts >= tonumber(ARGV[3]) then return -1 end
local owner = redis.call('GET', KEYS[2])
local active_hash = redis.call('GET', KEYS[3])
if owner == ARGV[1] and active_hash == ARGV[2] then
  redis.call('DEL', KEYS[1], KEYS[2], KEYS[3])
  return 1
end
if attempts == 0 then
  redis.call('SET', KEYS[1], '1', 'EX', ARGV[4])
else
  redis.call('INCR', KEYS[1])
end
return 0
"""


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verify_key(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        self.mailer = EmailSender()

    async def close(self) -> None:
        await self.redis.aclose()
        await self.mailer.close()

    async def _new_code(self, user: User) -> str:
        for _ in range(8):
            code = f"{secrets.randbelow(100_000_000):08d}"
            key = f"auth:verification:{_verify_key(code)}"
            if await self.redis.set(key, str(user.id), ex=settings.verification_code_ttl_seconds, nx=True):
                active_key = f"auth:verification:active:{user.id}"
                previous_hash = await self.redis.get(active_key)
                if previous_hash:
                    await self.redis.delete(f"auth:verification:{previous_hash}")
                await self.redis.set(active_key, _verify_key(code), ex=settings.verification_code_ttl_seconds)
                await self.redis.delete(f"auth:verification:attempts:{user.id}")
                return code
        raise RuntimeError("Could not generate a unique verification code")

    async def _send_verification(self, user: User, correlation_id: str | None = None) -> None:
        code = await self._new_code(user)
        try:
            await self.mailer.send_code(user.email, code, correlation_id or str(uuid4()))
        except Exception:
            await self.redis.delete(f"auth:verification:{_verify_key(code)}")
            raise

    async def register(self, body: RegisterBody) -> User:
        email = str(body.email).lower()
        existing = await self.session.scalar(select(User.id).where(func.lower(User.email) == email))
        if existing:
            raise HTTPException(status_code=409, detail="Email is already registered")
        existing_phone = await self.session.scalar(select(User.id).where(User.phone == body.phone))
        if existing_phone:
            raise HTTPException(status_code=409, detail="Phone is already registered")

        user = User(
            email=email,
            phone=body.phone,
            password_hash=hash_password(body.password),
            first_name=body.first_name,
            last_name=body.last_name,
            patronymic=body.patronymic,
            is_active=True,
            email_verified=False,
            phone_verified=False,
            notification_preferences={"listing": True, "messages": True, "security": True},
        )
        self.session.add(user)
        await self.session.flush()
        await self._send_verification(user)
        return user

    async def issue_session(self, user: User, device: DeviceInfo, ip: str | None) -> tuple[str, str]:
        session_id = uuid4()
        refresh = create_refresh_token(
            user.id,
            {"jti": str(session_id), "user_id": str(user.user_id)},
        )
        db_session = AuthSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=_token_hash(refresh),
            device_info={
                "user_agent": device.user_agent,
                "ip": ip or device.ip,
                "device_name": device.device_name,
            },
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        )
        self.session.add(db_session)
        await self.session.flush()
        access = create_access_token(
            user.id,
            {"user_id": str(user.user_id), "email": user.email, "role": user.role},
        )
        return access, refresh

    async def login(self, login: str, password: str, device: DeviceInfo, ip: str | None) -> tuple[User, str, str]:
        user = await self.session.scalar(
            select(User).where(or_(func.lower(User.email) == login.lower(), User.phone == login))
        )
        if not user or not verify_password(password, user.password_hash) or not user.is_active or user.is_banned:
            raise HTTPException(status_code=401, detail="Invalid login or password")
        if not user.email_verified:
            await self._send_verification(user)
            raise UnverifiedAccount(user.id)
        access, refresh = await self.issue_session(user, device, ip)
        await publisher.publish_security_event("login", str(user.user_id), {"device_name": device.device_name})
        return user, access, refresh

    async def refresh(self, token: str | None) -> tuple[str, str]:
        from app.security import decode_token

        if not token:
            raise HTTPException(status_code=401, detail="Refresh cookie is required")
        try:
            claims = decode_token(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
        if claims.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        db_session = await self.session.scalar(
            select(AuthSession).where(AuthSession.refresh_token_hash == _token_hash(token))
        )
        if not db_session or db_session.is_revoked or db_session.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Refresh session expired or revoked")
        user = await self.session.get(User, db_session.user_id)
        if not user or not user.is_active or user.is_banned or not user.email_verified:
            raise HTTPException(status_code=401, detail="User is unavailable")

        db_session.is_revoked = True
        session_id = uuid4()
        new_refresh = create_refresh_token(user.id, {"jti": str(session_id), "user_id": str(user.user_id)})
        self.session.add(AuthSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=_token_hash(new_refresh),
            device_info=db_session.device_info,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        ))
        access = create_access_token(user.id, {"user_id": str(user.user_id), "email": user.email, "role": user.role})
        return access, new_refresh

    async def revoke_sessions(self, user: User, token: str | None, all_devices: bool) -> None:
        if all_devices:
            await self.session.execute(
                update(AuthSession).where(AuthSession.user_id == user.id).values(is_revoked=True)
            )
        elif token:
            await self.session.execute(
                update(AuthSession)
                .where(AuthSession.user_id == user.id, AuthSession.refresh_token_hash == _token_hash(token))
                .values(is_revoked=True)
            )

    async def verify_email(self, code: str, challenge_user_id: int) -> User:
        digest = _verify_key(code)
        attempt_key = f"auth:verification:attempts:{challenge_user_id}"
        result = await self.redis.eval(
            _CONSUME_VERIFICATION_SCRIPT,
            3,
            attempt_key,
            f"auth:verification:{digest}",
            f"auth:verification:active:{challenge_user_id}",
            str(challenge_user_id),
            digest,
            5,
            settings.verification_code_ttl_seconds,
        )
        if result == -1:
            raise HTTPException(status_code=429, detail="Too many invalid verification attempts")
        if result != 1:
            raise HTTPException(status_code=400, detail="Verification code is invalid or expired")
        user = await self.session.get(User, challenge_user_id)
        if not user:
            raise HTTPException(status_code=400, detail="Verification code is invalid or expired")
        user.email_verified = True
        return user

    async def resend_code(self, user: User, channel: str) -> None:
        if channel == "phone":
            raise HTTPException(status_code=501, detail="SMS provider is not configured")
        if user.email_verified:
            return
        try:
            await self._send_verification(user)
        except EmailRateLimitError as exc:
            raise HTTPException(status_code=429, detail="Email sending rate limit exceeded") from exc

    async def start_password_reset(self, email: str) -> None:
        # Same response for existing and unknown addresses prevents account enumeration.
        user = await self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if not user:
            return
        reset_token = secrets.token_urlsafe(32)
        reset_key = f"auth:password-reset:{_token_hash(reset_token)}"
        await self.redis.set(reset_key, str(user.id), ex=600)
        # The same rate-limited and idempotent sender is used for the one-time reset credential.
        try:
            await self.mailer.send_code(user.email, reset_token, str(uuid4()), purpose="reset")
        except Exception:
            await self.redis.delete(reset_key)
            raise

    async def finish_password_reset(self, reset_token: str, new_password: str) -> None:
        key = f"auth:password-reset:{_token_hash(reset_token)}"
        user_id = await self.redis.get(key)
        if not user_id:
            raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
        user = await self.session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=400, detail="Reset token is invalid or expired")
        user.password_hash = hash_password(new_password)
        await self.session.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(is_revoked=True))
        await self.redis.delete(key)
        await publisher.publish_security_event("password_reset", str(user.user_id))

    async def change_password(self, user: User, current: str, new_password: str) -> None:
        if not verify_password(current, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.password_hash = hash_password(new_password)
        await self.session.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(is_revoked=True))
        await publisher.publish_security_event("password_changed", str(user.user_id))

    async def patch_profile(self, user: User, changes: ProfilePatch) -> User:
        values = changes.model_dump(exclude_unset=True)
        for field, value in values.items():
            setattr(user, field, value)
        return user


class UnverifiedAccount(Exception):
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
