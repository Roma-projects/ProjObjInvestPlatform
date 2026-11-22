"""Track moderation blacklist state in Auth."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_user_blacklist"
down_revision: Union[str, None] = "003_user_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_banned", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("users", sa.Column("ban_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "banned_at")
    op.drop_column("users", "ban_reason")
    op.drop_column("users", "is_banned")

