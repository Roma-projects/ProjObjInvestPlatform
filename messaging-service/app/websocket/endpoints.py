"""Для чего нужен этот файл:
Обрабатывает WebSocket-соединение — двусторонний канал связи для чата в реальном времени.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.schemas.message import SendMessageRequest
from app.services.chat_service import ChatService
from app.websocket.manager import manager

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


def _user_from_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            return None
        return int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        return None


@router.websocket("/ws/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: int) -> None:
    token = websocket.query_params.get("token")
    token_user = _user_from_token(token)
    if token_user is None or token_user != user_id:
        await websocket.close(code=4401)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if data.get("type") == "send":
                receiver_id = int(data.get("receiver_id", 0))
                content = str(data.get("content", "")).strip()
                if not receiver_id or not content:
                    await websocket.send_json(
                        {"type": "error", "detail": "receiver_id and content required"}
                    )
                    continue
                async with AsyncSessionLocal() as session:
                    service = ChatService(session)
                    msg = await service.send(
                        user_id,
                        SendMessageRequest(receiver_id=receiver_id, content=content),
                    )
                    await session.commit()
                    await websocket.send_json(
                        {"type": "message_ack", "data": msg.model_dump(mode="json")}
                    )
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception as exc:
        logger.exception("WS error: %s", exc)
        manager.disconnect(user_id, websocket)
