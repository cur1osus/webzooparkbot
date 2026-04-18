from __future__ import annotations


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
