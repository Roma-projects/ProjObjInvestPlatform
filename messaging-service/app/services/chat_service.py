"""Для чего нужен этот файл:
Реализует правила работы с сообщениями и диалогами. Сервисный слой связывает API, проверку данных и хранилище.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.rabbitmq.publisher import message_publisher
from app.repositories.message_repo import MessageRepository
from app.schemas.message import (
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
)
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = MessageRepository(session)

    async def conversations(self, user_id: int) -> list[ConversationResponse]:
        rows = await self.repo.list_conversations(user_id)
        result: list[ConversationResponse] = []
        for c in rows:
            peer = c.user2_id if c.user1_id == user_id else c.user1_id
            item = ConversationResponse.model_validate(c)
            item.peer_id = peer
            result.append(item)
        return result

    async def history(self, user_id: int, peer_id: int) -> list[MessageResponse]:
        messages = await self.repo.list_messages(user_id, peer_id)
        return [MessageResponse.model_validate(m) for m in messages]

    async def send(self, sender_id: int, body: SendMessageRequest) -> MessageResponse:
        msg = await self.repo.create_message(
            sender_id, body.receiver_id, body.content
        )
        response = MessageResponse.model_validate(msg)
        payload = response.model_dump(mode="json")
        await manager.send_personal(body.receiver_id, {"type": "message", "data": payload})
        await manager.send_personal(sender_id, {"type": "message_ack", "data": payload})
        await message_publisher.message_sent(msg)
        return response
