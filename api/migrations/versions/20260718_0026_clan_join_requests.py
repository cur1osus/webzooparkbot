"""Add owner-reviewed clan join requests."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260718_0026"
down_revision = "20260718_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clan_join_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("clan_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["clan_id"], ["clans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clan_id", "player_id", name="uq_clan_join_requests_pair"),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'rejected')", name="ck_clan_join_requests_status"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_clan_join_requests_clan_status",
        "clan_join_requests",
        ["clan_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_clan_join_requests_clan_status", table_name="clan_join_requests")
    op.drop_table("clan_join_requests")
