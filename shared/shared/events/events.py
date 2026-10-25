"""Для чего нужен этот файл:
Описывает имена и форматы событий, которыми микросервисы обмениваются через RabbitMQ.
"""

"""
RabbitMQ event schemas and topology constants.

Exchanges:
  - listings_events (topic)  → queues: search_index_queue, analytics_queue
  - messages_events (topic)  → queues: notifications_queue
  - notifications (fanout)   → queue: email_notifications_queue

Routing keys examples:
  - listing.created / listing.updated / listing.deleted
  - message.sent
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

EXCHANGE_LISTINGS = "listings_events"
EXCHANGE_MESSAGES = "messages_events"
EXCHANGE_NOTIFICATIONS = "notifications"

QUEUE_SEARCH_INDEX = "search_index_queue"
QUEUE_ANALYTICS = "analytics_queue"
QUEUE_NOTIFICATIONS = "notifications_queue"
QUEUE_EMAIL_NOTIFICATIONS = "email_notifications_queue"


class ListingCreatedEvent(BaseModel):
    event_type: str = "listing.created"
    listing_id: int
    owner_id: int
    title: str
    price: Decimal
    area: float
    rooms: int
    address: str
    lat: float | None = None
    lng: float | None = None
    type: str = "apartment"
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def routing_key(self) -> str:
        return "listing.created"


class ListingUpdatedEvent(BaseModel):
    event_type: str = "listing.updated"
    listing_id: int
    owner_id: int
    title: str
    price: Decimal
    area: float
    rooms: int
    address: str
    lat: float | None = None
    lng: float | None = None
    type: str = "apartment"
    status: str = "active"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def routing_key(self) -> str:
        return "listing.updated"


class ListingDeletedEvent(BaseModel):
    event_type: str = "listing.deleted"
    listing_id: int
    owner_id: int
    deleted_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def routing_key(self) -> str:
        return "listing.deleted"


class MessageSentEvent(BaseModel):
    event_type: str = "message.sent"
    message_id: int
    sender_id: int
    receiver_id: int
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def routing_key(self) -> str:
        return "message.sent"


class NotificationEvent(BaseModel):
    event_type: str = "notification"
    user_id: int
    channel: str = "email"
    subject: str
    body: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
