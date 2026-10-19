"""Отправка кодов Auth через SMTP с Redis-лимитами и идемпотентностью."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from email.message import EmailMessage

import aiosmtplib
import redis.asyncio as redis
from jinja2 import Environment, PackageLoader, select_autoescape

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
templates = Environment(
    loader=PackageLoader("app", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

_RATE_LIMIT_SCRIPT = """
local minute = redis.call('INCR', KEYS[1])
if minute == 1 then redis.call('EXPIRE', KEYS[1], 60) end
local hour = redis.call('INCR', KEYS[2])
if hour == 1 then redis.call('EXPIRE', KEYS[2], 3600) end
if minute > 1 or hour > 5 then return 0 end
return 1
"""


class EmailSender:
    """Проверяет лимит доставки и отправляет письмо с повторными попытками."""

    def __init__(self) -> None:
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        await self.redis.aclose()

    async def send_code(self, recipient: str, code: str, correlation_id: str, purpose: str = "verify") -> None:
        if not all((settings.smtp_host, settings.smtp_from_address)):
            raise RuntimeError("SMTP is not configured")

        address_hash = hashlib.sha256(recipient.strip().lower().encode()).hexdigest()
        sent_key = f"auth:email:sent:{correlation_id}"
        lock_key = f"auth:email:lock:{correlation_id}"
        if await self.redis.get(sent_key):
            return
        locked = await self.redis.set(lock_key, "1", ex=60, nx=True)
        if not locked:
            # A concurrent retry with the same ID must not send another email.
            for _ in range(10):
                await asyncio.sleep(0.1)
                if await self.redis.get(sent_key):
                    return
            raise RuntimeError("Email with this correlation_id is already being sent")

        try:
            allowed = await self.redis.eval(
                _RATE_LIMIT_SCRIPT,
                2,
                f"auth:email:minute:{address_hash}",
                f"auth:email:hour:{address_hash}",
            )
            if not allowed:
                raise EmailRateLimitError("Email rate limit exceeded")

            template = templates.get_template("verification_code.html")
            is_reset = purpose == "reset"
            title = "Сброс пароля" if is_reset else "Подтверждение адреса"
            action = "Введите временный токен для сброса пароля:" if is_reset else "Введите код подтверждения в приложении:"
            html = template.render(code=code, ttl_minutes=10, title=title, action=action)
            message = EmailMessage()
            message["From"] = settings.smtp_from_address
            message["To"] = recipient
            message["Subject"] = title
            message.set_content(f"{action} {code}. Срок действия — 10 минут.")
            message.add_alternative(html, subtype="html")

            for attempt in range(3):
                try:
                    await aiosmtplib.send(
                        message,
                        hostname=settings.smtp_host,
                        port=settings.smtp_port,
                        username=settings.smtp_user or None,
                        password=settings.smtp_password or None,
                        start_tls=settings.smtp_start_tls and settings.smtp_port != 465,
                        use_tls=settings.smtp_port == 465,
                        timeout=20,
                    )
                    await self.redis.set(sent_key, "1", ex=86400)
                    logger.info("Verification email sent correlation_id=%s", correlation_id)
                    return
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2**attempt)
        finally:
            await self.redis.delete(lock_key)


class EmailRateLimitError(Exception):
    """Raised when the per-recipient SMTP sending limits are exceeded."""
