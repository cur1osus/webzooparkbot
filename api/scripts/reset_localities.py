"""Keep one random locality per active player and refund prior locality purchases.

This is a one-time operational action for the current season. It is intentionally
idempotent: players who already have one locality are left alone, while players with
several localities are reset once and receive one ledger refund for their recorded
opening costs.
"""

from __future__ import annotations

import argparse
from random import SystemRandom

from sqlalchemy import select, update

from api.app.db.connection import get_session
from api.app.db.models import Animal, Locality, Player
from api.app.zoopark import ledger
from api.app.zoopark.catalog import HABITATS
from api.app.zoopark.season import active_season


random = SystemRandom()


def reset_localities(*, apply: bool) -> None:
    with get_session() as session:
        season = active_season(session)
        players = session.scalars(
            select(Player).where(Player.status == "active").with_for_update()
        ).all()

        total_refund = 0
        reset_count = 0
        for player in players:
            localities = session.scalars(
                select(Locality)
                .where(Locality.player_id == player.id, Locality.season_id == season.id)
                .with_for_update()
            ).all()

            if len(localities) > 1:
                keep = random.choice(localities)
                removed = [locality for locality in localities if locality.id != keep.id]
                refund = sum(int(locality.price_paid_rub) for locality in localities)

                removed_ids = [locality.id for locality in removed]
                session.execute(
                    update(Animal)
                    .where(Animal.locality_id.in_(removed_ids))
                    .values(locality_id=None)
                )
                for locality in removed:
                    session.delete(locality)

                keep.level = 0
                keep.price_paid_rub = 0
                if refund:
                    ledger.grant(session, player, "rub", refund, "locality_reset_refund")
                    total_refund += refund
                reset_count += 1
                print(f"{player.nickname}: kept {keep.habitat}, refunded {refund} ₽")
                continue

            if len(localities) == 1:
                refund = int(localities[0].price_paid_rub)
                localities[0].level = 0
                localities[0].price_paid_rub = 0
                if refund:
                    ledger.grant(session, player, "rub", refund, "locality_reset_refund")
                    total_refund += refund
                continue

            locality = Locality(
                player_id=player.id,
                season_id=season.id,
                habitat=random.choice(HABITATS),
                level=0,
                price_paid_rub=0,
            )
            session.add(locality)
            print(f"{player.nickname}: granted {locality.habitat}")

        if apply:
            session.commit()
        else:
            session.rollback()
        mode = "Applied" if apply else "Dry-run"
        print(f"{mode}: reset {reset_count} players; refund total {total_refund} ₽")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="commit the reset and refunds")
    reset_localities(apply=parser.parse_args().apply)
