"""Для чего нужен этот файл:
Миграция базы данных: upgrade применяет изменение таблиц, downgrade описывает обратный шаг. Alembic запускает их по команде.
"""

"""Initial listings + photos."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_listings"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("area", sa.Float(), nullable=False),
        sa.Column("rooms", sa.Integer(), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_listings_owner_id", "listings", ["owner_id"])
    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("is_main", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("photos")
    op.drop_index("ix_listings_owner_id", table_name="listings")
    op.drop_table("listings")
