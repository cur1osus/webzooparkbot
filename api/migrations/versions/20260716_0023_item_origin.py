"""Track where an item came from, so expeditions can drop items.

Revision ID: 20260716_0023
Revises: 20260716_0022
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260716_0023"
down_revision = "20260716_0022"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in inspect(op.get_bind()).get_columns(table)}


def _has_check(table: str, name: str) -> bool:
    return any(item.get("name") == name for item in inspect(op.get_bind()).get_check_constraints(table))


def upgrade() -> None:
    # Every item that exists today was forged and paid for, so backfilling "forge" is exact,
    # not a guess — and it is what keeps their resale price unchanged across this migration.
    with op.batch_alter_table("items") as batch_op:
        if not _has_column("items", "origin"):
            batch_op.add_column(
                sa.Column("origin", sa.String(16), nullable=False, server_default="forge")
            )
        if not _has_check("items", "ck_items_origin"):
            batch_op.create_check_constraint("ck_items_origin", "origin IN ('forge', 'expedition')")


def downgrade() -> None:
    # A dropped item has no create price to refund; leaving it behind after `origin` is gone
    # would silently make it sellable for the forge price it never cost.
    op.execute("DELETE FROM items WHERE origin = 'expedition'")
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_constraint("ck_items_origin", type_="check")
        batch_op.drop_column("origin")
