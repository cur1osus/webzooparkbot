"""Rename the legendary nickname cosmetic to the Google palette.

Revision ID: 20260712_0006
Revises: 20260712_0005
"""

from __future__ import annotations

from alembic import op


revision = "20260712_0006"
down_revision = "20260712_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE player_cosmetics SET cosmetic_id = 'google' WHERE cosmetic_id = 'liquid_gold'")
    op.execute("UPDATE players SET nickname_color = 'google' WHERE nickname_color = 'liquid_gold'")


def downgrade() -> None:
    op.execute("UPDATE player_cosmetics SET cosmetic_id = 'liquid_gold' WHERE cosmetic_id = 'google'")
    op.execute("UPDATE players SET nickname_color = 'liquid_gold' WHERE nickname_color = 'google'")
