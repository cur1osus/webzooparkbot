"""Add canonical mantissa/exponent columns for economy fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-09
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_COLUMNS: dict[str, list[str]] = {
    "users": [
        "rub",
        "usd",
        "paw_coins",
        "income_per_minute",
        "maintenance_per_minute",
        "amount_expenses_rub",
        "amount_expenses_usd",
        "amount_expenses_paw_coins",
    ],
    "webapp_extra": [
        "solo_daily_rub_won",
        "solo_daily_usd_won",
        "solo_daily_income_pm",
    ],
    "animals": ["price", "income"],
    "aviaries": ["price"],
    "user_aviary_states": ["current_price"],
    "random_merchants": ["price_with_discount", "price", "quantity_animals"],
    "transfer_money": ["one_piece_sum"],
    "sick_animal_events": ["cure_cost"],
    "donates": ["amount"],
    "games": ["amount_award"],
}


def _has_column(conn, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND COLUMN_NAME = :column "
            "LIMIT 1"
        ),
        {"table": table, "column": column},
    ).fetchone()
    return bool(row)


def _ensure_pair_columns(conn, table: str, column: str) -> None:
    if not _has_column(conn, table, column):
        return
    if not _has_column(conn, table, f"{column}_mantissa"):
        conn.execute(
            text(
                f"ALTER TABLE `{table}` "
                f"ADD COLUMN `{column}_mantissa` VARCHAR(80) NOT NULL DEFAULT '0'"
            )
        )
    if not _has_column(conn, table, f"{column}_exponent"):
        conn.execute(
            text(
                f"ALTER TABLE `{table}` "
                f"ADD COLUMN `{column}_exponent` INT NOT NULL DEFAULT 0"
            )
        )


def _backfill_pair(conn, table: str, column: str) -> None:
    if not _has_column(conn, table, column):
        return
    conn.execute(
        text(
            f"UPDATE `{table}` "
            f"SET `{column}_mantissa` = TRIM(LEADING '+' FROM CAST(COALESCE(`{column}`, 0) AS CHAR)), "
            f"`{column}_exponent` = 0 "
            f"WHERE `{column}_mantissa` IS NULL OR `{column}_mantissa` = '' OR `{column}_exponent` IS NULL OR (`{column}_mantissa` = '0' AND COALESCE(`{column}`, 0) <> 0)"
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "mysql":
        return
    for table, columns in TABLE_COLUMNS.items():
        for column in columns:
            _ensure_pair_columns(conn, table, column)
            _backfill_pair(conn, table, column)


def downgrade() -> None:
    pass
