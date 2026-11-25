"""Allow longer explanations for the reason a business is being sold."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_expand_sale_reason"
down_revision: Union[str, None] = "002_business_listings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "listings",
        "sale_reason",
        existing_type=sa.String(length=200),
        type_=sa.String(length=1000),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "listings",
        "sale_reason",
        existing_type=sa.String(length=1000),
        type_=sa.String(length=200),
        existing_nullable=True,
    )