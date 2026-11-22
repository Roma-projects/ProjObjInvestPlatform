from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModerationCase(Base):
    __tablename__ = "moderation_cases"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    listing_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=False, index=True)
    seller_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    verification_level: Mapped[str] = mapped_column(String(16), default="basic", nullable=False)
    listing_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    analytics_reports: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    document_refs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    decision: Mapped[str | None] = mapped_column(String(16))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decision_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BlacklistEntry(Base):
    __tablename__ = "user_blacklist"
    __table_args__ = (
        Index("uq_user_blacklist_active_user", "user_id", unique=True, postgresql_where=text("is_active IS TRUE")),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    banned_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))


class ModerationOutboxEvent(Base):
    __tablename__ = "moderation_outbox_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    routing_key: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))

