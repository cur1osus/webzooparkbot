"""Rebase ruble and dollar denominations by 100.

PawCoins are premium currency and intentionally keep their existing scale. Values below
one new unit are kept at one so registration, bonuses and other small rewards do not
disappear during the rebase.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0007"
down_revision = "20260712_0006"
branch_labels = None
depends_on = None


def _scaled(value: int) -> int:
    if value == 0:
        return 0
    result = (abs(int(value)) + 50) // 100
    return max(1, result) if value > 0 else -max(1, result)


def _scale_column(
    conn,
    table: str,
    column: str,
    *,
    key_columns: tuple[str, ...] = ("id",),
    minimum: bool = True,
) -> None:
    keys = ", ".join(key_columns)
    rows = conn.execute(sa.text(f"SELECT {keys}, {column} FROM {table}")).fetchall()
    updates = []
    for row in rows:
        key_values = row[:len(key_columns)]
        value = row[len(key_columns)]
        raw = int(value or 0)
        scaled = _scaled(raw) if minimum else (0 if raw == 0 else int(round(raw / 100)))
        updates.append({**dict(zip(key_columns, key_values)), "value": scaled})
    if updates:
        where = " AND ".join(f"{key} = :{key}" for key in key_columns)
        conn.execute(sa.text(f"UPDATE {table} SET {column} = :value WHERE {where}"), updates)


def _multiply_column(conn, table: str, column: str) -> None:
    conn.execute(sa.text(f"UPDATE {table} SET {column} = {column} * 100"))


def upgrade() -> None:
    conn = op.get_bind()

    # Rebase the ledger first, then rebuild player balances from the rebased history so
    # SUM(ledger.delta) == players.balance_* remains true even for old small entries.
    ledger_rows = conn.execute(
        sa.text("SELECT id, player_id, currency, delta FROM ledger ORDER BY player_id, currency, id")
    ).fetchall()
    running: dict[tuple[int, str], int] = {}
    totals: dict[tuple[int, str], int] = {}
    for row_id, player_id, currency, delta in ledger_rows:
        delta_value = int(delta)
        scaled_delta = _scaled(delta_value) if currency in {"rub", "usd"} else delta_value
        key = (int(player_id), str(currency))
        running[key] = running.get(key, 0) + scaled_delta
        totals[key] = running[key]
        conn.execute(
            sa.text("UPDATE ledger SET delta = :delta, balance_after = :balance WHERE id = :id"),
            {"id": row_id, "delta": scaled_delta, "balance": running[key]},
        )

    player_rows = conn.execute(sa.text("SELECT id, income_rub_per_min, upkeep_rub_per_min FROM players")).fetchall()
    for player_id, income, upkeep in player_rows:
        conn.execute(
            sa.text(
                "UPDATE players SET balance_rub = :rub, balance_usd = :usd, "
                "income_rub_per_min = :income, upkeep_rub_per_min = :upkeep WHERE id = :id"
            ),
            {
                "id": player_id,
                "rub": totals.get((int(player_id), "rub"), 0),
                "usd": totals.get((int(player_id), "usd"), 0),
                "income": _scaled(int(income or 0)),
                "upkeep": _scaled(int(upkeep or 0)),
            },
        )

    for entry in (
        ("localities", "price_paid_rub"),
        ("merchant_offers", "list_price_rub"),
        ("pack_openings", "price_paid_rub"),  # legacy column; stores paid USD now
        ("duels", "stake_rub"),
        ("solo_stats", "won_rub", ("player_id",)),
        ("solo_stats", "lost_rub", ("player_id",)),
        ("transfers", "amount_per_claim"),
        ("transfer_claims", "amount_rub", ("transfer_id", "player_id")),
    ):
        table, column, *key = entry
        _scale_column(conn, table, column, key_columns=key[0] if key else ("id",))

    # Daily bonuses are mixed-currency rows: PawCoins stay as-is, rubles are rebased,
    # and small dollar bonuses use the minimum-one rule.
    bonus_rows = conn.execute(sa.text("SELECT id, currency, amount FROM daily_bonuses")).fetchall()
    for row_id, currency, amount in bonus_rows:
        if currency == "paw":
            continue
        conn.execute(
            sa.text("UPDATE daily_bonuses SET amount = :amount WHERE id = :id"),
            {"id": row_id, "amount": _scaled(int(amount))},
        )

    treasury_rows = conn.execute(sa.text("SELECT currency, balance FROM treasury")).fetchall()
    for currency, balance in treasury_rows:
        if currency == "paw":
            continue
        conn.execute(
            sa.text("UPDATE treasury SET balance = :balance WHERE currency = :currency"),
            {"currency": currency, "balance": _scaled(int(balance))},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for table, column in (
        ("players", "income_rub_per_min"),
        ("players", "upkeep_rub_per_min"),
        ("localities", "price_paid_rub"),
        ("merchant_offers", "list_price_rub"),
        ("pack_openings", "price_paid_rub"),
        ("duels", "stake_rub"),
        ("solo_stats", "won_rub"),
        ("solo_stats", "lost_rub"),
        ("transfers", "amount_per_claim"),
        ("transfer_claims", "amount_rub"),
    ):
        # This is a best-effort rollback for local development only; values that were
        # rounded up from less than 100 cannot be restored exactly.
        _multiply_column(conn, table, column)

    conn.execute(sa.text("UPDATE daily_bonuses SET amount = amount * 100 WHERE currency <> 'paw'"))
    conn.execute(sa.text("UPDATE treasury SET balance = balance * 100 WHERE currency <> 'paw'"))

    # Rebuild ledger balances after restoring their deltas; player balances follow below.
    rows = conn.execute(sa.text("SELECT id, player_id, currency, delta FROM ledger ORDER BY player_id, currency, id")).fetchall()
    running: dict[tuple[int, str], int] = {}
    for row_id, player_id, currency, delta in rows:
        restored = int(delta) * 100 if currency in {"rub", "usd"} else int(delta)
        key = (int(player_id), str(currency))
        running[key] = running.get(key, 0) + restored
        conn.execute(sa.text("UPDATE ledger SET delta = :delta, balance_after = :balance WHERE id = :id"), {"id": row_id, "delta": restored, "balance": running[key]})
    for player_id in {int(row[0]) for row in conn.execute(sa.text("SELECT id FROM players")).fetchall()}:
        conn.execute(sa.text("UPDATE players SET balance_rub = :rub, balance_usd = :usd WHERE id = :id"), {"id": player_id, "rub": running.get((player_id, "rub"), 0), "usd": running.get((player_id, "usd"), 0)})
