"""Persist unresolved solo match presentations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260721_0037"
down_revision = "20260720_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solo_matches",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("stake_rub", sa.BigInteger(), nullable=False),
        sa.Column("won", sa.Boolean(), nullable=False),
        sa.Column("rub_delta", sa.BigInteger(), nullable=False),
        sa.Column("player_score", sa.Integer(), nullable=False),
        sa.Column("ai_score", sa.Integer(), nullable=False),
        sa.Column("history", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_solo_matches_player"),
        sa.CheckConstraint(
            "kind IN ('basketball', 'football', 'dice', 'darts', 'bowling')",
            name="ck_solo_matches_kind",
        ),
        sa.CheckConstraint("stake_rub > 0", name="ck_solo_matches_stake"),
    )


def downgrade() -> None:
    op.drop_table("solo_matches")
