"""Let players pin animals they care about."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260720_0034"
down_revision = "20260720_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "animals",
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("animals", "is_favorite")
