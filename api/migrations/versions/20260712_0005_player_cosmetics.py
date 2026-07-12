"""Sell nickname colors as permanent PawCoin cosmetics.

Revision ID: 20260712_0005
Revises: 20260712_0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260712_0005"
down_revision = "20260712_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_cosmetics",
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cosmetic_id", sa.String(length=16), primary_key=True),
        sa.Column("purchased_at", sa.DateTime(), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    # Preserve colors selected during the brief free beta period.
    op.execute(
        "INSERT INTO player_cosmetics (player_id, cosmetic_id, purchased_at) "
        "SELECT id, nickname_color, CURRENT_TIMESTAMP FROM players WHERE nickname_color <> 'ivory'"
    )


def downgrade() -> None:
    op.drop_table("player_cosmetics")
