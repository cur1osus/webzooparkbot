"""The bank safe: a shared code round and its sealed daily guesses."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260720_0030"
down_revision = "20260720_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "safe_rounds",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("secret", sa.String(length=16), nullable=False),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("solved_at", sa.DateTime(), nullable=True),
        sa.Column("prize_usd", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("resolved_day", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("prize_usd >= 0", name="ck_safe_rounds_prize"),
        sa.PrimaryKeyConstraint("id"),
        # One round may open per day, which is what makes the concurrent "first request of
        # the day creates the round" path collapse to a single row.
        sa.UniqueConstraint("opened_on", name="uq_safe_rounds_opened_on"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "safe_attempts",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("round_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("exact", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("misplaced", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["round_id"], ["safe_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    # Both the board and the per-player attempt count filter on (round, day).
    op.create_index("ix_safe_attempts_round_day", "safe_attempts", ["round_id", "day"])


def downgrade() -> None:
    op.drop_index("ix_safe_attempts_round_day", table_name="safe_attempts")
    op.drop_table("safe_attempts")
    op.drop_table("safe_rounds")
