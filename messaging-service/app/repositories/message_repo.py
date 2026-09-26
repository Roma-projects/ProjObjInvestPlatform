"""Для чего нужен этот файл:
Собирает операции чтения и записи в базе данных, отделяя запросы к хранилищу от правил приложения.
"""

from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Conversation, Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_conversation(
        self, user_a: int, user_b: int
    ) -> Conversation:
        u1, u2 = sorted([user_a, user_b])
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.user1_id == u1, Conversation.user2_id == u2
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv
        conv = Conversation(user1_id=u1, user2_id=u2)
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def list_conversations(self, user_id: int) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(
                or_(
                    Conversation.user1_id == user_id,
                    Conversation.user2_id == user_id,
                )
            )
            .order_by(Conversation.last_message_at.desc().nullslast())
        )
        return list(result.scalars().all())

    async def list_messages(
        self, user_id: int, peer_id: int, limit: int = 100
    ) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(
                or_(
                    and_(Message.sender_id == user_id, Message.receiver_id == peer_id),
                    and_(Message.sender_id == peer_id, Message.receiver_id == user_id),
                )
            )
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_message(
        self, sender_id: int, receiver_id: int, content: str
    ) -> Message:
        conv = await self.get_or_create_conversation(sender_id, receiver_id)
        msg = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            status="sent",
        )
        self.session.add(msg)
        conv.last_message_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(msg)
        return msg
