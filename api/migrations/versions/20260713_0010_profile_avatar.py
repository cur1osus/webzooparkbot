"""Allow profile avatars to reference unlocked achievement TGS files."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260713_0010"
down_revision = "20260712_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.alter_column(
            "profile_emoji",
            existing_type=sa.String(length=16),
            type_=sa.String(length=64),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.alter_column(
            "profile_emoji",
            existing_type=sa.String(length=64),
            type_=sa.String(length=16),
            existing_nullable=True,
        )
