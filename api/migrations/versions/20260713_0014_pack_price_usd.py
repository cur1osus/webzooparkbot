"""Correct the pack purchase column name after the economy rebase.

Revision ID: 20260713_0014
Revises: 20260713_0013
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260713_0014"
down_revision = "20260713_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pack_openings") as batch:
        batch.alter_column(
            "price_paid_rub",
            new_column_name="price_paid_usd",
            existing_type=sa.BigInteger(),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("pack_openings") as batch:
        batch.alter_column(
            "price_paid_usd",
            new_column_name="price_paid_rub",
            existing_type=sa.BigInteger(),
            existing_nullable=False,
        )
