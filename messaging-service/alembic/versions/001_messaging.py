"""Для чего нужен этот файл:
Миграция базы данных: upgrade применяет изменение таблиц, downgrade описывает обратный шаг. Alembic запускает их по команде.
"""

"""Initial messages + conversations."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_messaging"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user1_id", sa.Integer(), nullable=False),
        sa.Column("user2_id", sa.Integer(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user1_id", "conversations", ["user1_id"])
    op.create_index("ix_conversations_user2_id", "conversations", ["user2_id"])
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("receiver_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_index("ix_messages_receiver_id", "messages", ["receiver_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_receiver_id", table_name="messages")
    op.drop_index("ix_messages_sender_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_user2_id", table_name="conversations")
    op.drop_index("ix_conversations_user1_id", table_name="conversations")
    op.drop_table("conversations")
