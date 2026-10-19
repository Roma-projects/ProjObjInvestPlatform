"""MongoDB-хранилище диалогов и сообщений с курсорами и мягким удалением."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings

settings = get_settings()


class MessageStore:
    """Одна изолированная MongoDB на сервис; пары пользователей определяют диалог."""

    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        database = self.client.get_default_database()
        self.conversations = database["conversations"]
        self.messages = database["messages"]

    async def connect(self) -> None:
        await self.conversations.create_index("participants")
        await self.conversations.create_index("participant_pair", unique=True)
        await self.conversations.create_index([("last_message_at", -1)])
        await self.messages.create_index([("sender_id", 1), ("client_message_id", 1)], unique=True)
        await self.messages.create_index([("conversation_id", 1), ("created_at", -1)])

    async def close(self) -> None:
        self.client.close()

    async def create_message(self, command: dict[str, Any]) -> dict[str, Any]:
        sender = str(UUID(command["sender_id"]))
        recipient = str(UUID(command["participant_id"]))
        if sender == recipient:
            raise ValueError("A conversation requires two different users")
        pair = sorted([sender, recipient])
        now = datetime.now(timezone.utc)
        conversation = await self.conversations.find_one_and_update(
            {"participant_pair": pair},
            {"$setOnInsert": {"participants": pair, "participant_pair": pair,
                              "created_at": now, "unread_counts": {sender: 0, recipient: 0}}},
            upsert=True, return_document=True,
        )
        message_id = str(command["event_id"])
        item = {
            "_id": message_id,
            "conversation_id": str(conversation["_id"]),
            "sender_id": sender,
            "receiver_id": recipient,
            "client_message_id": str(command["client_message_id"]),
            "text": str(command["text"]),
            "created_at": now,
            "deleted_for_all": False,
            "deleted_for_users": [],
        }
        try:
            await self.messages.insert_one(item)
        except Exception as exc:
            # A repeated client_message_id is an idempotent replay, not a new chat message.
            if await self.messages.find_one({"sender_id": sender, "client_message_id": item["client_message_id"]}):
                return await self.messages.find_one({"sender_id": sender, "client_message_id": item["client_message_id"]})
            raise exc
        await self.conversations.update_one(
            {"_id": conversation["_id"]},
            {"$set": {"last_message_at": now, "last_message": item},
             "$inc": {f"unread_counts.{recipient}": 1}},
        )
        return item

    async def get_or_create_conversation(self, owner_id: str, participant_id: str) -> dict[str, Any]:
        owner, peer = str(UUID(owner_id)), str(UUID(participant_id))
        if owner == peer:
            raise ValueError("A conversation requires two different users")
        pair = sorted([owner, peer])
        return await self.conversations.find_one_and_update(
            {"participant_pair": pair},
            {"$setOnInsert": {"participants": pair, "participant_pair": pair,
                              "created_at": datetime.now(timezone.utc),
                              "unread_counts": {owner: 0, peer: 0}}},
            upsert=True, return_document=True,
        )

    async def list_conversations(self, user_id: str, cursor: str | None, unread_only: bool, limit: int) -> dict[str, Any]:
        uid = str(UUID(user_id))
        query: dict[str, Any] = {"participants": uid}
        if unread_only:
            query[f"unread_counts.{uid}"] = {"$gt": 0}
        if cursor:
            stamp, object_id = self._decode_cursor(cursor)
            query["$or"] = [{"last_message_at": {"$lt": stamp}},
                             {"last_message_at": stamp, "_id": {"$lt": object_id}}]
        rows = await self.conversations.find(query).sort([("last_message_at", -1), ("_id", -1)]).limit(limit + 1).to_list(limit + 1)
        more = len(rows) > limit
        rows = rows[:limit]
        return {"items": [self._json_safe(row, uid) for row in rows],
                "next_cursor": self._encode_cursor(rows[-1]) if more and rows else None}

    async def history(self, user_id: str, conversation_id: str, cursor: str | None, limit: int) -> dict[str, Any]:
        uid = str(UUID(user_id))
        conversation = await self.conversations.find_one({"_id": conversation_id, "participants": uid})
        if not conversation:
            raise LookupError("Conversation not found")
        query: dict[str, Any] = {"conversation_id": conversation_id, "deleted_for_all": False,
                                 "deleted_for_users": {"$ne": uid}}
        if cursor:
            stamp, object_id = self._decode_cursor(cursor)
            query["$or"] = [{"created_at": {"$lt": stamp}},
                             {"created_at": stamp, "_id": {"$lt": object_id}}]
        rows = await self.messages.find(query).sort([("created_at", -1), ("_id", -1)]).limit(limit + 1).to_list(limit + 1)
        more = len(rows) > limit
        rows = rows[:limit]
        return {"items": [self._json_safe(row) for row in rows],
                "next_cursor": self._encode_cursor(rows[-1]) if more and rows else None}

    async def delete_message(self, user_id: str, message_id: str, delete_for_all: bool) -> bool:
        uid = str(UUID(user_id))
        message = await self.messages.find_one({"_id": message_id})
        if not message or uid not in {message["sender_id"], message["receiver_id"]}:
            return False
        if delete_for_all:
            if message["sender_id"] != uid:
                return False
            await self.messages.update_one({"_id": message_id}, {"$set": {"deleted_for_all": True}})
        else:
            await self.messages.update_one({"_id": message_id}, {"$addToSet": {"deleted_for_users": uid}})
        return True

    async def mark_read(self, user_id: str, message_ids: list[str]) -> int:
        uid = str(UUID(user_id))
        targets = await self.messages.find(
            {"_id": {"$in": message_ids}, "receiver_id": uid, "read_at": None},
            {"conversation_id": 1},
        ).to_list(len(message_ids))
        result = await self.messages.update_many(
            {"_id": {"$in": message_ids}, "receiver_id": uid, "read_at": None},
            {"$set": {"read_at": datetime.now(timezone.utc)}},
        )
        for conversation_id in {item["conversation_id"] for item in targets}:
            remaining = await self.messages.count_documents({
                "conversation_id": conversation_id, "receiver_id": uid,
                "read_at": None, "deleted_for_all": False,
            })
            await self.conversations.update_one(
                {"_id": conversation_id}, {"$set": {f"unread_counts.{uid}": remaining}}
            )
        return result.modified_count

    @staticmethod
    def _encode_cursor(row: dict[str, Any]) -> str:
        stamp = row.get("last_message_at") or row.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
        value = json.dumps({"time": stamp.isoformat(), "id": str(row["_id"])})
        return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, str]:
        try:
            value = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
            return datetime.fromisoformat(value["time"]), value["id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Invalid cursor") from exc

    @staticmethod
    def _json_safe(row: dict[str, Any], owner: str | None = None) -> dict[str, Any]:
        safe = dict(row)
        safe["id"] = str(safe.pop("_id"))
        for key in ("created_at", "last_message_at"):
            if isinstance(safe.get(key), datetime):
                safe[key] = safe[key].isoformat()
        if owner and isinstance(safe.get("unread_counts"), dict):
            safe["unread_count"] = safe["unread_counts"].get(owner, 0)
            peer = next((item for item in safe.get("participants", []) if item != owner), None)
            safe["participant_id"] = peer
            safe.pop("unread_counts", None)
        if isinstance(safe.get("last_message"), dict):
            safe["last_message"] = MessageStore._json_safe(safe["last_message"])
        return safe


store = MessageStore()
