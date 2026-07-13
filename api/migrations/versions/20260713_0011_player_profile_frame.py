"""Store a server-validated cosmetic avatar frame.

Revision ID: 20260713_0011
Revises: 20260713_0010
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260713_0011"
down_revision = "20260713_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("profile_frame", sa.String(length=24), nullable=False, server_default="none"),
    )


def downgrade() -> None:
    op.drop_column("players", "profile_frame")
