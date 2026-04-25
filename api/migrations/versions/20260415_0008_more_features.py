from __future__ import annotations

from types import SimpleNamespace

import sqlalchemy as sa
from sqlalchemy import text

try:
    from alembic import op
except Exception:  # pragma: no cover - keeps helper unit tests importable without Alembic.
    op = SimpleNamespace(create_table=lambda *args, **kwargs: None, get_bind=lambda: None)


revision = "0008"
down_revision = "20260407_0001"
branch_labels = None
depends_on = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        text("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:table LIMIT 1"),
        {"table": table},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    if not _table_exists("zoopark_transfer_links"):
        op.create_table(
            "zoopark_transfer_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("link_key", sa.String(length=32), nullable=False),
            sa.Column("creator_id", sa.Integer(), nullable=False),
            sa.Column("total_amount", sa.BigInteger(), nullable=False),
            sa.Column("rub_per_claim", sa.BigInteger(), nullable=False),
            sa.Column("max_claims", sa.Integer(), nullable=False),
            sa.Column("claims", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("active", sa.SmallInteger(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    pass
