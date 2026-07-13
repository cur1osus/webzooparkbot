"""Store a server-validated cosmetic profile wallpaper.

Revision ID: 20260713_0012
Revises: 20260713_0011
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260713_0012"
down_revision = "20260713_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("profile_wallpaper", sa.String(length=24), nullable=False, server_default="none"),
    )


def downgrade() -> None:
    op.drop_column("players", "profile_wallpaper")
