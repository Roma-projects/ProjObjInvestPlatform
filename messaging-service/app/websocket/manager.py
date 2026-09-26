"""Для чего нужен этот файл:
Управляет активными WebSocket-подключениями, чтобы сервер мог отправлять сообщения клиентам в реальном времени.
"""

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.setdefault(user_id, []).append(websocket)
        logger.info("WS connected user_id=%s", user_id)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        conns = self.active.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns and user_id in self.active:
            del self.active[user_id]
        logger.info("WS disconnected user_id=%s", user_id)

    async def send_personal(self, user_id: int, message: dict[str, Any]) -> None:
        for ws in list(self.active.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning("WS send failed user_id=%s: %s", user_id, exc)


manager = ConnectionManager()
