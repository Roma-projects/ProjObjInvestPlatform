"""Хранит уведомления в отдельной MongoDB и отправляет их онлайн-пользователям."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient
from starlette.websockets import WebSocket

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    """Сохраняет in-app уведомления и держит активные WebSocket-соединения."""

    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        self.collection = self.client.get_default_database()["notifications"]
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self) -> None:
        await self.collection.create_index([("user_id", 1), ("created_at", -1)])
        await self.collection.create_index("event_id", unique=True, sparse=True)

    async def close(self) -> None:
        self.client.close()

    async def add_connection(self, user_id: str, socket: WebSocket) -> None:
        await socket.accept()
        self.connections.setdefault(user_id, set()).add(socket)
        pending = await self.collection.find({"user_id": user_id, "is_read": False}).sort("created_at", -1).limit(100).to_list(100)
        for row in reversed(pending):
            await socket.send_json({
                "event_id": row.get("event_id"),
                "type": row["type"], "payload": row["payload"],
                "created_at": row["created_at"].isoformat(), "is_read": False,
            })

    async def mark_read(self, user_id: str, event_id: str) -> None:
        await self.collection.update_one(
            {"user_id": user_id, "event_id": event_id}, {"$set": {"is_read": True}}
        )

    def remove_connection(self, user_id: str, socket: WebSocket) -> None:
        sockets = self.connections.get(user_id)
        if sockets:
            sockets.discard(socket)
            if not sockets:
                self.connections.pop(user_id, None)

    async def send(self, event: dict[str, Any]) -> None:
        """Persist one event, then push the same safe notification over WebSocket."""
        user_id = event.get("user_id") or event.get("receiver_id")
        if not user_id:
            logger.info("Dropping notification without recipient: event=%s", event.get("event"))
            return
        notice_type = event.get("event") or event.get("event_type") or "notification"
        payload = {
            "listing_id": event.get("listing_id"),
            "message_id": event.get("message_id"),
            "status": event.get("status"),
            "reason": event.get("user_safe_reason"),
        }
        notice = {
            "event_id": event.get("event_id") or str(uuid4()),
            "type": notice_type,
            "payload": payload,
            "created_at": datetime.now(timezone.utc),
            "is_read": False,
        }
        if notice["event_id"]:
            await self.collection.update_one(
                {"event_id": notice["event_id"]}, {"$setOnInsert": {**notice, "user_id": str(user_id)}}, upsert=True
            )
        else:
            await self.collection.insert_one({**notice, "user_id": str(user_id)})
        for socket in tuple(self.connections.get(str(user_id), ())):
            try:
                await socket.send_json({
                    "event_id": notice["event_id"],
                    "type": notice_type, "payload": payload,
                    "created_at": notice["created_at"].isoformat(), "is_read": False,
                })
            except Exception:
                self.remove_connection(str(user_id), socket)


notification_service = NotificationService()
