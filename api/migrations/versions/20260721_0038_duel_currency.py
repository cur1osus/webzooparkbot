"""Let a duel be wagered in dollars, not only rubles.

Adds a `currency` column to `duels`. Every existing lobby was a ruble stake, and the
server default keeps that true for any row written by an old process mid-deploy, so no
backfill is needed. `stake_rub` keeps its name but now holds the stake in this `currency`.

Revision ID: 20260721_0038
Revises: 20260721_0037
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260721_0038"
down_revision = "20260721_0037"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in inspect(op.get_bind()).get_columns(table)}


def _has_check(table: str, name: str) -> bool:
    return any(item.get("name") == name for item in inspect(op.get_bind()).get_check_constraints(table))


def upgrade() -> None:
    with op.batch_alter_table("duels") as batch_op:
        if not _has_column("duels", "currency"):
            batch_op.add_column(
                sa.Column("currency", sa.String(8), nullable=False, server_default="rub")
            )
        if not _has_check("duels", "ck_duels_currency"):
            batch_op.create_check_constraint(
                "ck_duels_currency", "currency IN ('rub', 'usd')"
            )


def downgrade() -> None:
    with op.batch_alter_table("duels") as batch_op:
        batch_op.drop_constraint("ck_duels_currency", type_="check")
        batch_op.drop_column("currency")
