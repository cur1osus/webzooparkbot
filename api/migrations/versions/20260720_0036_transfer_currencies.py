"""Allow money giveaways to use rubles or dollars."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260720_0036"
down_revision = "20260720_0035"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    op.add_column("transfers", sa.Column("currency", sa.String(length=3), nullable=False, server_default="rub"))
    if not _is_sqlite():
        op.create_check_constraint("ck_transfers_currency", "transfers", "currency IN ('rub', 'usd')")


def downgrade() -> None:
    if not _is_sqlite():
        op.drop_constraint("ck_transfers_currency", "transfers", type_="check")
    op.drop_column("transfers", "currency")
