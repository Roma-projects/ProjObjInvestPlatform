"""Add an explicit role used to protect moderator-only Listing operations."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_user_roles"
down_revision: Union[str, None] = "002_identity_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(32), nullable=False, server_default="user"))


def downgrade() -> None:
    op.drop_column("users", "role")
