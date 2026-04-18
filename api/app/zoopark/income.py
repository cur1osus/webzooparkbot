from __future__ import annotations

from datetime import datetime, timezone

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


def accrue_income(cur, user: dict, income_rub_per_min: int) -> dict:
    """Add elapsed passive income to user balance. Returns updated user dict."""
    uid = user["id"]
    cur.execute("SELECT last_income_at, balance_seq FROM webapp_extra WHERE user_id=%s", (uid,))
    row = cur.fetchone()
    if row is None:
        return user

    now = datetime.now(timezone.utc)
    last_income_at = row.get("last_income_at")

    accrued = 0
    if last_income_at is not None and income_rub_per_min > 0:
        if hasattr(last_income_at, "tzinfo") and last_income_at.tzinfo is None:
            last_income_at = last_income_at.replace(tzinfo=timezone.utc)
        elapsed_mins = (now - last_income_at).total_seconds() / 60.0
        accrued = int(elapsed_mins * income_rub_per_min)

    new_rub = int(user["rub"]) + accrued
    new_seq = int(now.timestamp() * 1000)

    if accrued > 0:
        cur.execute("UPDATE users SET rub=%s WHERE id=%s", (new_rub, uid))
    cur.execute(
        "UPDATE webapp_extra SET last_income_at=%s, balance_seq=%s WHERE user_id=%s",
        (now, new_seq, uid),
    )

    user = dict(user)
    user["rub"] = new_rub
    return user


def calc_pack_income(cur, user_id: int) -> int:
    cur.execute(
        """SELECT pa.survival, pa.appearance, pa.size_trait,
                  pa.habitat AS animal_habitat, pl.habitat AS locality_habitat
           FROM pack_animals pa
           LEFT JOIN player_localities pl ON pa.locality_id = pl.id
           WHERE pa.user_id=%s AND pa.is_alive=1 AND (pa.dies_at IS NULL OR pa.dies_at > NOW())
             AND pa.in_expedition IS NULL""",
        (user_id,),
    )
    total = 0
    for row in cur.fetchall():
        bonus = 1.5 if row["locality_habitat"] and row["locality_habitat"] == row["animal_habitat"] else 1.0
        total += pack_animal_income(row, bonus)
    return total
