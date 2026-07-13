"""Add transactional Telegram notifications and a season rollover lock.

Revision ID: 20260713_0013
Revises: 20260713_0012
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260713_0013"
down_revision = "20260713_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "season_gate",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.execute(sa.text("INSERT INTO season_gate (id) VALUES (1)"))

    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="ck_notification_outbox_attempts"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe_key"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_notification_outbox_delivery",
        "notification_outbox",
        ["sent_at", "available_at", "locked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_delivery", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_table("season_gate")
