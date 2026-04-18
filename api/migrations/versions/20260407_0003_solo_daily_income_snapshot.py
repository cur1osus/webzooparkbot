"""Add solo_daily_income_pm snapshot column to webapp_extra

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-07
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, column: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": table, "c": column}).fetchone()
    return (row[0] if row else 0) > 0


def _has_table(conn, table: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) as cnt FROM information_schema.TABLES"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {"t": table}).fetchone()
    return (row[0] if row else 0) > 0


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "mysql":
        return
    if not _has_table(conn, "webapp_extra"):
        return
    if not _has_column(conn, "webapp_extra", "solo_daily_income_pm"):
        conn.execute(text(
            "ALTER TABLE `webapp_extra` ADD COLUMN solo_daily_income_pm BIGINT NOT NULL DEFAULT 0"
        ))


def downgrade() -> None:
    pass
