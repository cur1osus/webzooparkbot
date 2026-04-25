from __future__ import annotations

from datetime import datetime, timezone
from math import trunc

from api.app.zoopark.catalog import DIVERSITY_BONUS_PER_SPECIES
from api.app.db.tables import (
    ZOOPARK_ANIMALS_TABLE,
    ZOOPARK_EXTRA_TABLE,
    ZOOPARK_LOCALITIES_TABLE,
    ZOOPARK_PACK_ANIMALS_TABLE,
    ZOOPARK_SICK_EVENTS_TABLE,
    ZOOPARK_USERS_TABLE,
)

PACK_BASE_INCOME = 5000

PACK_INCOME_MULT = {
    "survival": {"low": 0.7, "medium": 1.0, "high": 1.3},
    "appearance": {"low": 0.6, "medium": 1.0, "high": 1.5},
    "size_trait": {"low": 0.8, "medium": 1.0, "high": 1.4},
}


def pack_animal_income(animal: dict, habitat_bonus: float = 1.0) -> int:
    return int(
        PACK_BASE_INCOME
        * PACK_INCOME_MULT["survival"][animal["survival"]]
        * PACK_INCOME_MULT["appearance"][animal["appearance"]]
        * PACK_INCOME_MULT["size_trait"][animal["size_trait"]]
        * habitat_bonus
    )


def calc_sick_expenses(cur, user_id: int) -> int:
    cur.execute(
        f"SELECT COALESCE(SUM(penalty_rub_per_min), 0) AS total FROM {ZOOPARK_SICK_EVENTS_TABLE} WHERE user_id=%s",
        (user_id,),
    )
    row = cur.fetchone() or {}
    return int(row.get("total") or 0)


def calc_legacy_income(cur, user_id: int) -> int:
    cur.execute(
        f"""SELECT
               COALESCE(SUM(CAST(income AS SIGNED) * CAST(quantity AS SIGNED)), 0) AS base_income,
               COUNT(*) AS species_count
           FROM {ZOOPARK_ANIMALS_TABLE}
           WHERE user_id=%s AND quantity>0""",
        (user_id,),
    )
    row = cur.fetchone() or {}
    base_income = int(row.get("base_income") or 0)
    species_count = int(row.get("species_count") or 0)
    if base_income <= 0 or species_count <= 0:
        return 0

    diversity_multiplier = 1 + (species_count * DIVERSITY_BONUS_PER_SPECIES)
    return int(base_income * diversity_multiplier)


def accrue_income(cur, user: dict, income_rub_per_min: int, expenses_rub_per_min: int = 0) -> dict:
    """Add elapsed passive net income to user balance. Returns updated user dict."""
    uid = user["id"]
    cur.execute(f"SELECT last_income_at, balance_seq FROM {ZOOPARK_EXTRA_TABLE} WHERE user_id=%s", (uid,))
    row = cur.fetchone()
    if row is None:
        return user

    now = datetime.now(timezone.utc)
    last_income_at = row.get("last_income_at")
    net_rub_per_min = income_rub_per_min - expenses_rub_per_min

    accrued = 0
    if last_income_at is not None and net_rub_per_min != 0:
        if hasattr(last_income_at, "tzinfo") and last_income_at.tzinfo is None:
            last_income_at = last_income_at.replace(tzinfo=timezone.utc)
        elapsed_mins = (now - last_income_at).total_seconds() / 60.0
        accrued = trunc(elapsed_mins * net_rub_per_min)

    current_rub = int(user["rub"])
    new_rub = max(0, current_rub + accrued)
    new_seq = int(now.timestamp() * 1000)

    if new_rub != current_rub:
        cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (new_rub, uid))
    cur.execute(
        f"UPDATE {ZOOPARK_EXTRA_TABLE} SET last_income_at=%s, balance_seq=%s WHERE user_id=%s",
        (now, new_seq, uid),
    )

    user = dict(user)
    user["rub"] = new_rub
    user["balance_seq"] = new_seq
    return user


def calc_pack_income(cur, user_id: int) -> int:
    cur.execute(
        f"""SELECT pa.survival, pa.appearance, pa.size_trait,
                  pa.habitat AS animal_habitat, pl.habitat AS locality_habitat
           FROM {ZOOPARK_PACK_ANIMALS_TABLE} pa
           LEFT JOIN {ZOOPARK_LOCALITIES_TABLE} pl ON pa.locality_id = pl.id
           WHERE pa.user_id=%s AND pa.is_alive=1 AND (pa.dies_at IS NULL OR pa.dies_at > NOW())
             AND pa.in_expedition IS NULL""",
        (user_id,),
    )
    total = 0
    for row in cur.fetchall():
        bonus = 1.5 if row["locality_habitat"] and row["locality_habitat"] == row["animal_habitat"] else 1.0
        total += pack_animal_income(row, bonus)
    return total


def sync_passive_balance(cur, user: dict) -> tuple[dict, int, int]:
    income_rub_per_min = calc_legacy_income(cur, user["id"]) + calc_pack_income(cur, user["id"])
    expenses_rub_per_min = calc_sick_expenses(cur, user["id"])
    return accrue_income(cur, user, income_rub_per_min, expenses_rub_per_min), income_rub_per_min, expenses_rub_per_min
