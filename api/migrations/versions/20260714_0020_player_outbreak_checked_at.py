"""Anchor for passive disease outbreaks.

Revision ID: 20260714_0020
Revises: 20260714_0019
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260714_0020"
down_revision = "20260714_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable with no backfill: existing players start at NULL, which the first sync reads
    # as "never checked" and quietly sets to now — so nobody eats a huge retroactive outbreak
    # window, and we avoid seeding a UTC timestamp from the DB server's (possibly non-UTC) clock.
    op.add_column("players", sa.Column("outbreak_checked_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("players", "outbreak_checked_at")
