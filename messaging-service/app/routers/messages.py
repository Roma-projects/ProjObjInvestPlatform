"""Для чего нужен этот файл:
Описывает HTTP-маршруты этой части API и связывает адреса и методы запросов с функциями-обработчиками.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.message import (
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])
bearer = HTTPBearer(auto_error=False)
settings = get_settings()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return int(payload["sub"])


async def get_chat_service(session: AsyncSession = Depends(get_db)) -> ChatService:
    return ChatService(session)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user_id: int = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
) -> list[ConversationResponse]:
    return await service.conversations(user_id)


@router.get("/conversation/{peer_id}", response_model=list[MessageResponse])
async def conversation_history(
    peer_id: int,
    user_id: int = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
) -> list[MessageResponse]:
    return await service.history(user_id, peer_id)


@router.post("/send", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    body: SendMessageRequest,
    user_id: int = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
) -> MessageResponse:
    return await service.send(user_id, body)
