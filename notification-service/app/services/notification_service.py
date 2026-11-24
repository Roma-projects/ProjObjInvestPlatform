"""Хранит уведомления в отдельной MongoDB и отправляет их онлайн-пользователям."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
import secrets
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
        database = self.client.get_default_database()
        self.collection = database["notifications"]
        self.blocked_users_collection = database["blocked_users"]
        self.websocket_tickets_collection = database["websocket_tickets"]
        self.connections: dict[str, set[WebSocket]] = {}
        self.blocked_users: set[str] = set()

    async def connect(self) -> None:
        await self.collection.create_index([("user_id", 1), ("created_at", -1)])
        await self.collection.create_index("event_id", unique=True, sparse=True)
        await self.websocket_tickets_collection.create_index("expires_at", expireAfterSeconds=0)

    async def close(self) -> None:
        self.client.close()

    async def add_connection(self, user_id: str, socket: WebSocket) -> bool:
        if user_id in self.blocked_users or await self.blocked_users_collection.find_one({"_id": user_id}):
            self.blocked_users.add(user_id)
            await socket.close(code=4403, reason="Account is blocked")
            return False
        if len(self.connections.get(user_id, ())) >= 5:
            await socket.close(code=4429, reason="Too many connections")
            return False
        # The WebSocket route accepts only after validating its one-use ticket.
        self.connections.setdefault(user_id, set()).add(socket)
        pending = await self.collection.find({"user_id": user_id, "is_read": False}).sort("created_at", -1).limit(100).to_list(100)
        for row in reversed(pending):
            await socket.send_json({
                "event_id": row.get("event_id"),
                "type": row["type"], "payload": row["payload"],
                "created_at": row["created_at"].isoformat(), "is_read": False,
            })
        return True

    async def block_user(self, user_id: str) -> None:
        self.blocked_users.add(user_id)
        await self.blocked_users_collection.update_one({"_id": user_id}, {"$set": {"blocked": True}}, upsert=True)
        for socket in tuple(self.connections.pop(user_id, ())):
            try:
                await socket.close(code=4403, reason="Account is blocked")
            except Exception:
                logger.debug("WebSocket for blocked user was already closed: user=%s", user_id)

    async def unblock_user(self, user_id: str) -> None:
        self.blocked_users.discard(user_id)
        await self.blocked_users_collection.delete_one({"_id": user_id})

    async def list_notifications(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = await self.collection.find(
            {"user_id": user_id},
            {"_id": 0, "event_id": 1, "type": 1, "payload": 1, "created_at": 1, "is_read": 1},
        ).sort("created_at", -1).limit(limit).to_list(limit)
        return [
            {
                "event_id": row.get("event_id"),
                "type": row.get("type", "notification"),
                "payload": row.get("payload", {}),
                "created_at": (
                    row["created_at"].replace(tzinfo=timezone.utc)
                    if row["created_at"].tzinfo is None else row["created_at"]
                ).isoformat(),
                "is_read": bool(row.get("is_read", False)),
            }
            for row in rows
        ]

    async def issue_websocket_ticket(self, user_id: str) -> str:
        ticket = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        await self.websocket_tickets_collection.insert_one({
            "_id": ticket,
            "user_id": user_id,
            "expires_at": now + timedelta(seconds=30),
        })
        return ticket

    async def consume_websocket_ticket(self, ticket: str) -> str | None:
        if not ticket or len(ticket) > 128:
            return None
        row = await self.websocket_tickets_collection.find_one_and_delete({
            "_id": ticket,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        })
        return str(row["user_id"]) if row else None

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
