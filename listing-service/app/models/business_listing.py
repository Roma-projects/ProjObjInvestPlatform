"""Хранит объявления о продаже готового бизнеса по форме из технического задания."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, Numeric, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BusinessListing(Base):
    __tablename__ = "listings"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    business_type: Mapped[str | None] = mapped_column(String(40))
    property_type: Mapped[str | None] = mapped_column(String(40))
    transfer_method: Mapped[str | None] = mapped_column(String(40))
    deal_composition: Mapped[str | None] = mapped_column(String(40))
    business_name: Mapped[str | None] = mapped_column(String(200))
    short_description: Mapped[str | None] = mapped_column(String(500))
    full_description: Mapped[str | None] = mapped_column(Text)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    stock_included: Mapped[bool | None] = mapped_column(Boolean)
    stock_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    country: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    street: Mapped[str | None] = mapped_column(String(200))
    house: Mapped[str | None] = mapped_column(String(50))
    query: Mapped[str | None] = mapped_column(String(500))
    area_sqm: Mapped[float | None] = mapped_column(Float)
    floor_number: Mapped[int | None] = mapped_column(Integer)
    has_separate_entrance: Mapped[bool | None] = mapped_column(Boolean)
    parking_spaces: Mapped[int | None] = mapped_column(Integer)
    ceiling_height: Mapped[float | None] = mapped_column(Float)
    property_condition: Mapped[str | None] = mapped_column(String(40))
    equipment_list: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    documents: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    staff_count: Mapped[int | None] = mapped_column(Integer)
    staff_details: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    working_hours: Mapped[str | None] = mapped_column(String(100))
    business_age_months: Mapped[int | None] = mapped_column(Integer)
    has_licenses: Mapped[bool | None] = mapped_column(Boolean)
    has_contracts: Mapped[bool | None] = mapped_column(Boolean)
    sale_reason: Mapped[str | None] = mapped_column(String(1000))
    stay_as_consultant_months: Mapped[int | None] = mapped_column(Integer)
    files: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(2048))
    tax_system: Mapped[str | None] = mapped_column(String(100))
    monthly_financials: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    average_check: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    monthly_orders: Mapped[int | None] = mapped_column(Integer)
    monthly_clients_unique: Mapped[int | None] = mapped_column(Integer)
    cost_structure: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    seasonality_months: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    peak_hours: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    supplier_contracts: Mapped[bool | None] = mapped_column(Boolean)
    supplier_details: Mapped[str | None] = mapped_column(Text)
    debts_receivable: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    debts_payable: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    legal_claims: Mapped[bool | None] = mapped_column(Boolean)
    legal_claims_details: Mapped[str | None] = mapped_column(Text)
    equipment_lease: Mapped[bool | None] = mapped_column(Boolean)
    monthly_loan_payments: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    customer_base_size: Mapped[int | None] = mapped_column(Integer)
    repeat_customer_rate: Mapped[float | None] = mapped_column(Float)
    seller_name: Mapped[str | None] = mapped_column(String(200))
    seller_status: Mapped[str | None] = mapped_column(String(20))
    seller_phone: Mapped[str | None] = mapped_column(String(32))
    seller_email: Mapped[str | None] = mapped_column(String(255))
    seller_inn: Mapped[str | None] = mapped_column(String(12))
    seller_ogrnip: Mapped[str | None] = mapped_column(String(15))
    analytics_results: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    verification_status: Mapped[str | None] = mapped_column(String(16))
    revenue_trend: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BlockedUser(Base):
    """Local projection of the moderation blacklist for write-side enforcement."""

    __tablename__ = "blocked_users"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    reason: Mapped[str | None] = mapped_column(String(500))
    blocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
