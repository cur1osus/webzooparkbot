"""Re-settle and recompute every player's income/upkeep under the current catalog.

Run this once after a balance change so the cached `income_rub_per_min` /
`upkeep_rub_per_min` on every player reflect the new numbers immediately, instead of
lazily on each player's next visit. `sync_player_income` first accrues what the old
stored rate owed (settling the elapsed period at the rate that actually applied), then
writes the freshly recomputed rate — so this is safe to run at any time and idempotent.

    python -m api.scripts.recompute_income            # dry-run, prints the diff
    python -m api.scripts.recompute_income --apply     # commit the recomputed rates
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from api.app.db.connection import get_session
from api.app.db.models import Player
from api.app.zoopark.income import sync_player_income


def recompute_income(*, apply: bool) -> None:
    with get_session() as session:
        players = session.scalars(select(Player).with_for_update()).all()

        changed = 0
        for player in players:
            before = (int(player.income_rub_per_min), int(player.upkeep_rub_per_min))
            income, upkeep = sync_player_income(session, player)
            if (income, upkeep) != before:
                changed += 1
                print(
                    f"{player.nickname}: income {before[0]}→{income}, "
                    f"upkeep {before[1]}→{upkeep} ₽/мин"
                )

        if apply:
            session.commit()
        else:
            session.rollback()
        mode = "Applied" if apply else "Dry-run"
        print(f"{mode}: {len(players)} players, {changed} rate changes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="commit the recomputed rates")
    recompute_income(apply=parser.parse_args().apply)
