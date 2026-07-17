"""Wipe every player's game progress and open a fresh season.

A season rollover taken to its logical end: the whole game state is cleared, not just
the season-scoped tables. Everything a player built — zoo, localities, expeditions,
forge items, cosmetics, clans, balances, development tracks, game stats — is removed.

The one thing that survives is a player's *donated* PawCoins. A player keeps the full
sum of every PawCoin they ever bought with Telegram Stars (`star_payments.paw_credited`,
minus refunds), even PawCoins they had already spent: real money is given back in full.
In-game-earned PawCoins are wiped like everything else.

Never touched: `players` identity (only their game fields are zeroed), `star_payments`
(the donation record and Telegram's idempotency key), `telegram_updates`, the seeded
catalogue (`species`), `bank_rates`, `treasury` (the house's own money, not a player's
progress), `custom_achievements` medal templates (owner content, re-awardable), and the
`game_maintenance` technical-break row itself.

The `ledger` is truncated and the surviving donation balance is re-granted as a single
`season_reset` entry per player, so the `SUM(delta) == balance` invariant that
`ledger.reconcile` checks still holds afterwards.

Safe by default: a dry run that prints exactly what it would do and rolls back. Pass
`--apply` to commit. Refuses to run unless the technical break is active, so it cannot
fire on a live game; `--force` overrides that guard.
"""

from __future__ import annotations

import argparse
from datetime import timedelta

from sqlalchemy import delete, func, select, update

from api.app.db.connection import get_session
from api.app.db.models import (
    Animal,
    BreedingAttempt,
    Clan,
    ClanMember,
    CocktailDay,
    CocktailRound,
    CustomAchievementRecipient,
    DailyBonus,
    Duel,
    Expedition,
    ExpeditionMember,
    Item,
    ItemProperty,
    ItemSet,
    ItemSetMember,
    LedgerEntry,
    Locality,
    MerchantOffer,
    NotificationOutbox,
    PackOpening,
    Player,
    PlayerCosmetic,
    Season,
    SoloStats,
    StarPayment,
    Transfer,
    TransferClaim,
    utcnow,
)
from api.app.zoopark import ledger, maintenance
from api.app.zoopark.catalog import SEASON_LENGTH_DAYS

# Deleted whole, children before parents so no foreign key is ever left dangling. `players`
# is not here: it is kept and its game fields are zeroed instead. `ledger` is last because
# the donation re-grant below writes fresh rows into it.
WIPE_ORDER = [
    ExpeditionMember,
    Expedition,
    MerchantOffer,
    PackOpening,
    BreedingAttempt,
    Animal,
    Locality,
    ItemProperty,
    ItemSetMember,
    ItemSet,
    Item,
    PlayerCosmetic,
    ClanMember,
    Clan,
    SoloStats,
    Duel,
    CocktailRound,
    CocktailDay,
    DailyBonus,
    TransferClaim,
    Transfer,
    CustomAchievementRecipient,
    NotificationOutbox,
    LedgerEntry,
]


def _donations_by_player(session) -> dict[int, int]:
    """player_id -> total PawCoins bought with Stars and not refunded."""
    rows = session.execute(
        select(StarPayment.player_id, func.coalesce(func.sum(StarPayment.paw_credited), 0))
        .where(StarPayment.refunded_at.is_(None))
        .group_by(StarPayment.player_id)
    ).all()
    return {int(player_id): int(total) for player_id, total in rows if int(total) > 0}


def reset_season(*, apply: bool, force: bool) -> None:
    with get_session() as session:
        maint = maintenance.status(session)
        if not maint["active"] and not force:
            raise SystemExit(
                "Technical break is not active — refusing to wipe a live game. "
                "Start the break in the admin panel first, or pass --force."
            )

        player_count = session.scalar(select(func.count()).select_from(Player)) or 0

        print("Rows to be removed:")
        for model in WIPE_ORDER:
            count = session.scalar(select(func.count()).select_from(model)) or 0
            print(f"  {model.__tablename__:<32} {count}")

        donations = _donations_by_player(session)
        total_donation = sum(donations.values())
        print(
            f"\nPlayers: {player_count}. "
            f"Donation PawCoins preserved: {total_donation} across {len(donations)} players."
        )

        # 1. Close the current season(s) and open a new one. `active_season` will hand this
        #    fresh row out on the next request; per-player season membership is created lazily.
        now = utcnow()
        session.execute(update(Season).where(Season.status == "active").values(status="finished"))
        new_season = Season(
            starts_at=now,
            ends_at=now + timedelta(days=SEASON_LENGTH_DAYS),
            status="active",
        )
        session.add(new_season)
        session.flush()

        # 2. Break the self-references inside `animals` before the table is deleted, so no
        #    parent_* / locality_id foreign key blocks the delete regardless of row order.
        session.execute(
            update(Animal).values(parent_a_id=None, parent_b_id=None, locality_id=None)
        )
        for model in WIPE_ORDER:
            session.execute(delete(model))

        # 3. Zero every game field on every player in one statement, PawCoins included; the
        #    donation is added back as ledger movements right after.
        session.execute(
            update(Player).values(
                balance_rub=0,
                balance_usd=0,
                balance_paw=0,
                vet_level=0,
                genetics_level=0,
                expedition_level=0,
                income_rub_per_min=0,
                upkeep_rub_per_min=0,
                income_synced_at=now,
                outbreak_checked_at=now,
                nickname_color="ivory",
                profile_frame="none",
                profile_wallpaper="none",
                profile_emoji=None,
            )
        )

        # 4. Re-grant preserved donations through the ledger, so balance and ledger reconcile.
        if donations:
            players = session.scalars(
                select(Player).where(Player.id.in_(donations)).with_for_update()
            ).all()
            for player in players:
                ledger.grant(session, player, "paw", donations[player.id], "season_reset")

        # 5. Prove the money invariant before committing anything.
        for player_id in donations:
            total, stored = ledger.reconcile(session, player_id, "paw")
            if total != stored:
                raise SystemExit(
                    f"Ledger mismatch for player {player_id}: ledger={total} balance={stored}. "
                    "Aborting without commit."
                )

        print(f"\nNew season #{new_season.id}: {new_season.starts_at:%Y-%m-%d} → {new_season.ends_at:%Y-%m-%d}")

        if apply:
            session.commit()
            print("Applied: progress wiped, donations restored, new season is live.")
        else:
            session.rollback()
            print("Dry-run: nothing was written. Re-run with --apply to commit.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wipe all progress and start a new season.")
    parser.add_argument("--apply", action="store_true", help="commit the wipe (default: dry-run)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="run even if the technical break is not active",
    )
    args = parser.parse_args()
    reset_season(apply=args.apply, force=args.force)
