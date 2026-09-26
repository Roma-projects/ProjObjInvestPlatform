"""Для чего нужен этот файл:
Готовит уведомления при событиях в системе. Сервисный слой связывает API, проверку данных и хранилище.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NotificationService:
    """MVP: log notifications instead of sending real emails."""

    async def send(self, payload: dict[str, Any]) -> None:
        channel = payload.get("channel", "email")
        user_id = payload.get("user_id")
        subject = payload.get("subject", "")
        body = payload.get("body", "")
        logger.info(
            "NOTIFY channel=%s user_id=%s subject=%s body=%s",
            channel,
            user_id,
            subject,
            body,
        )
        # Future: SMTP / SMS / push providers


notification_service = NotificationService()
