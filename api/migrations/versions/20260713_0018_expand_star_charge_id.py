"""Allow Telegram Stars charge identifiers."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260713_0018"
down_revision = "20260713_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("star_payments", recreate="always") as batch:
            batch.alter_column(
                "charge_id",
                existing_type=sa.String(length=128),
                type_=sa.String(length=255),
                existing_nullable=False,
            )
        return

    op.alter_column(
        "star_payments",
        "charge_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("star_payments", recreate="always") as batch:
            batch.alter_column(
                "charge_id",
                existing_type=sa.String(length=255),
                type_=sa.String(length=128),
                existing_nullable=False,
            )
        return

    op.alter_column(
        "star_payments",
        "charge_id",
        existing_type=sa.String(length=255),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
