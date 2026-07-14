"""Bring the web clan system up to parity with the legacy bot."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260714_0019"
down_revision = "20260714_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clans", sa.Column("specialization", sa.String(length=16), nullable=True))



def downgrade() -> None:
    op.drop_column("clans", "specialization")
