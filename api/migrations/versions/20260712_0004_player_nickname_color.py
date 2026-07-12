"""Store a server-validated cosmetic nickname color.

Revision ID: 20260712_0004
Revises: 20260712_0003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260712_0004"
down_revision = "20260712_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("nickname_color", sa.String(length=16), nullable=False, server_default="ivory"),
    )


def downgrade() -> None:
    op.drop_column("players", "nickname_color")
