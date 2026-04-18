"""Convert overflow-prone bigint economy fields to decimal

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-09
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_type(conn, table: str, column: str) -> str | None:
    row = conn.execute(
        text(
            "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return str(row[0]).lower() if row and row[0] else None


def _ensure_decimal(
    conn, table: str, column: str, nullable: bool, default: str | None
) -> None:
    column_type = _column_type(conn, table, column)
    if column_type is None or column_type == "decimal(65,0)":
        return
    null_sql = "NULL" if nullable else "NOT NULL"
    default_sql = f" DEFAULT {default}" if default is not None else ""
    conn.execute(
        text(
            f"ALTER TABLE `{table}` MODIFY COLUMN `{column}` DECIMAL(65,0) {null_sql}{default_sql}"
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "mysql":
        return
    _ensure_decimal(conn, "users", "paw_coins", False, "0")
    _ensure_decimal(conn, "users", "amount_expenses_paw_coins", False, "0")
    _ensure_decimal(conn, "webapp_extra", "solo_daily_rub_won", True, "0")
    _ensure_decimal(conn, "webapp_extra", "solo_daily_usd_won", True, "0")
    _ensure_decimal(conn, "webapp_extra", "solo_daily_income_pm", False, "0")
    _ensure_decimal(conn, "random_merchants", "price_with_discount", False, None)
    _ensure_decimal(conn, "random_merchants", "price", False, None)
    _ensure_decimal(conn, "random_merchants", "quantity_animals", False, None)
    _ensure_decimal(conn, "donates", "amount", False, None)


def downgrade() -> None:
    pass
