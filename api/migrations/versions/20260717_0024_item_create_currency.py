"""Record the currency an item was forged with, so resale refunds in that currency.

Closes the arbitrage where an item forged for a flat 350 PawCoins resold for a flat $32 000
(40% of the $80k dollar-forge base) regardless of what actually paid for it — turning the
forge into a Stars→dollars laundromat. Resale now refunds 40% of the *create* price in the
*same* currency it was paid in.

Revision ID: 20260717_0024
Revises: 20260716_0023
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260717_0024"
down_revision = "20260716_0023"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in inspect(op.get_bind()).get_columns(table)}


def _has_check(table: str, name: str) -> bool:
    return any(item.get("name") == name for item in inspect(op.get_bind()).get_check_constraints(table))


def upgrade() -> None:
    # Nullable with no backfill on purpose: NULL means "nobody bought this" (an expedition drop
    # or a merge result) *and* covers every item forged before this column existed. The resale
    # code treats a NULL create_currency on a `forge` item exactly as it treated it before —
    # a dollar refund — so existing items keep their price to the cent across this migration.
    with op.batch_alter_table("items") as batch_op:
        if not _has_column("items", "create_currency"):
            batch_op.add_column(sa.Column("create_currency", sa.String(8), nullable=True))
        if not _has_check("items", "ck_items_create_currency"):
            batch_op.create_check_constraint(
                "ck_items_create_currency",
                "create_currency IS NULL OR create_currency IN ('usd', 'paw')",
            )


def downgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_constraint("ck_items_create_currency", type_="check")
        batch_op.drop_column("create_currency")
