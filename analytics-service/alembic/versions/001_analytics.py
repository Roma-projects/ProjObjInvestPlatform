"""Для чего нужен этот файл:
Миграция базы данных: upgrade применяет изменение таблиц, downgrade описывает обратный шаг. Alembic запускает их по команде.
"""

"""Initial analytics + price_history."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_analytics"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analytics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("rent_estimate", sa.Numeric(14, 2), nullable=False),
        sa.Column("investment_score", sa.Float(), nullable=False),
        sa.Column("ml_model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_listing_id", "analytics", ["listing_id"])
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_history_listing_id", "price_history", ["listing_id"])


def downgrade() -> None:
    op.drop_index("ix_price_history_listing_id", table_name="price_history")
    op.drop_table("price_history")
    op.drop_index("ix_analytics_listing_id", table_name="analytics")
    op.drop_table("analytics")
