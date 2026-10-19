"""Move the old property schema aside and create the UUID business-listing schema."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_business_listings"
down_revision: Union[str, None] = "001_listings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb(name: str, default: str = "[]") -> sa.Column:
    return sa.Column(name, postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text(f"'{default}'::jsonb"))


def upgrade() -> None:
    # Preserve the previously shipped real-estate API and all existing rows.
    op.rename_table("listings", "property_listings")
    op.rename_table("photos", "property_photos")
    op.execute("ALTER INDEX ix_listings_owner_id RENAME TO ix_property_listings_owner_id")

    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_type", sa.String(40)),
        sa.Column("property_type", sa.String(40)),
        sa.Column("transfer_method", sa.String(40)),
        sa.Column("deal_composition", sa.String(40)),
        sa.Column("business_name", sa.String(200)),
        sa.Column("short_description", sa.String(500)),
        sa.Column("full_description", sa.Text()),
        sa.Column("sale_price", sa.Numeric(16, 2)),
        sa.Column("stock_included", sa.Boolean()),
        sa.Column("stock_value", sa.Numeric(16, 2)),
        sa.Column("country", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("street", sa.String(200)),
        sa.Column("house", sa.String(50)),
        sa.Column("query", sa.String(500)),
        sa.Column("area_sqm", sa.Float()),
        sa.Column("floor_number", sa.Integer()),
        sa.Column("has_separate_entrance", sa.Boolean()),
        sa.Column("parking_spaces", sa.Integer()),
        sa.Column("ceiling_height", sa.Float()),
        sa.Column("property_condition", sa.String(40)),
        _jsonb("equipment_list"),
        _jsonb("documents", "{}"),
        sa.Column("staff_count", sa.Integer()),
        _jsonb("staff_details"),
        sa.Column("working_hours", sa.String(100)),
        sa.Column("business_age_months", sa.Integer()),
        sa.Column("has_licenses", sa.Boolean()),
        sa.Column("has_contracts", sa.Boolean()),
        sa.Column("sale_reason", sa.String(200)),
        sa.Column("stay_as_consultant_months", sa.Integer()),
        _jsonb("files", "{}"),
        sa.Column("video_url", sa.String(2048)),
        sa.Column("tax_system", sa.String(100)),
        _jsonb("monthly_financials"),
        sa.Column("average_check", sa.Numeric(16, 2)),
        sa.Column("monthly_orders", sa.Integer()),
        sa.Column("monthly_clients_unique", sa.Integer()),
        _jsonb("cost_structure"),
        _jsonb("seasonality_months"),
        _jsonb("peak_hours"),
        sa.Column("supplier_contracts", sa.Boolean()),
        sa.Column("supplier_details", sa.Text()),
        sa.Column("debts_receivable", sa.Numeric(16, 2)),
        sa.Column("debts_payable", sa.Numeric(16, 2)),
        sa.Column("legal_claims", sa.Boolean()),
        sa.Column("legal_claims_details", sa.Text()),
        sa.Column("equipment_lease", sa.Boolean()),
        sa.Column("monthly_loan_payments", sa.Numeric(16, 2)),
        sa.Column("customer_base_size", sa.Integer()),
        sa.Column("repeat_customer_rate", sa.Float()),
        sa.Column("seller_name", sa.String(200)),
        sa.Column("seller_status", sa.String(20)),
        sa.Column("seller_phone", sa.String(32)),
        sa.Column("seller_email", sa.String(255)),
        sa.Column("seller_inn", sa.String(12)),
        sa.Column("seller_ogrnip", sa.String(15)),
        _jsonb("analytics_results", "{}"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("verification_status", sa.String(16)),
        sa.Column("revenue_trend", sa.String(16)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_listings_user_id", "listings", ["user_id"])
    op.create_index("ix_listings_status", "listings", ["status"])
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("routing_key", sa.String(120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(500)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_events_state", "outbox_events", ["state"])


def downgrade() -> None:
    op.drop_index("ix_outbox_events_state", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_listings_status", table_name="listings")
    op.drop_index("ix_listings_user_id", table_name="listings")
    op.drop_table("listings")
    op.rename_table("property_photos", "photos")
    op.rename_table("property_listings", "listings")
    op.execute("ALTER INDEX ix_property_listings_owner_id RENAME TO ix_listings_owner_id")
