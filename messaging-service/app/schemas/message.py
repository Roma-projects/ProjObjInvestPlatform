"""Для чего нужен этот файл:
Описывает и проверяет формат данных API. Pydantic сверяет входящие запросы с этими схемами.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SendMessageRequest(BaseModel):
    receiver_id: int
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    receiver_id: int
    content: str
    status: str
    created_at: datetime
    read_at: datetime | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user1_id: int
    user2_id: int
    last_message_at: datetime | None = None
    peer_id: int | None = None
