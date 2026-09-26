"""Для чего нужен этот файл:
Получает сообщения из RabbitMQ и обрабатывает события других сервисов, не требуя прямого HTTP-вызова.
"""

"""Optional consumer stub for message-side reactions."""

import logging

logger = logging.getLogger(__name__)


class MessageConsumer:
    async def start(self) -> None:
        logger.info("Messaging consumer idle (events published outbound)")

    async def stop(self) -> None:
        return None


consumer = MessageConsumer()
