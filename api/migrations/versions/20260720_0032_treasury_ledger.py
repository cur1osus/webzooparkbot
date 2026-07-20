"""Journal every movement of the house's money."""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from alembic import op


revision = "20260720_0032"
down_revision = "20260720_0031"
branch_labels = None
depends_on = None

CURRENCIES = ("rub", "usd", "paw")


def upgrade() -> None:
    op.create_table(
        "treasury_ledger",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("delta", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("ref_table", sa.String(length=32), nullable=True),
        sa.Column("ref_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            " OR ".join(f"currency = '{value}'" for value in CURRENCIES),
            name="ck_treasury_ledger_currency",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_treasury_ledger_currency_created", "treasury_ledger", ["currency", "created_at"])

    # Whatever is in the treasury right now predates the journal, so it is booked as one
    # opening balance. Without it `SUM(delta) == balance` would be false from the first
    # day and the invariant would be worthless exactly where it matters — on production.
    op.execute(
        sa.text(
            "INSERT INTO treasury_ledger (currency, delta, balance_after, reason, created_at) "
            "SELECT currency, balance, balance, 'opening_balance', :now FROM treasury WHERE balance <> 0"
        ).bindparams(now=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
    )


def downgrade() -> None:
    op.drop_index("ix_treasury_ledger_currency_created", table_name="treasury_ledger")
    op.drop_table("treasury_ledger")
