from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DecisionBody(BaseModel):
    verdict: Literal["approve", "reject"]
    reason: str | None = Field(default=None, min_length=3, max_length=500)
    verification_level: Literal["basic", "deep"] = "basic"


class BlacklistCreate(BaseModel):
    user_id: UUID
    reason: str = Field(min_length=3, max_length=500)


class CatalogRemovalBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ModerationCaseRead(BaseModel):
    id: UUID
    listing_id: UUID
    seller_id: UUID
    status: str
    verification_level: str
    listing_snapshot: dict
    analytics_reports: dict
    document_fields: list[str]
    decision: str | None
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None


class BlacklistEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    reason: str
    banned_by: UUID
    created_at: datetime

