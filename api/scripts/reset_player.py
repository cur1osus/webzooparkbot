"""Wipe one player's game progress and optionally credit them a fixed PawCoin balance.

The single-player twin of `reset_season`: it clears everything one player built — zoo,
localities, expeditions, forge items, cosmetics, clan membership, balances, development
tracks, game stats, and their whole ledger — while leaving their identity row (nickname,
telegram_id, registration) and their `star_payments` donation record untouched.

After the wipe every balance is zero. `--paw N` then credits N PawCoins through the ledger
as a single `season_reset` entry, so the `SUM(delta) == balance` invariant still holds.

Safe by default: a dry run that prints what it would do and rolls back. Pass `--apply` to
commit. Identify the player by `--telegram-id` or `--player-id`.

    python -m api.scripts.reset_player --telegram-id 8499419510 --paw 1450 --apply
"""

from __future__ import annotations

import argparse

from sqlalchemy import delete, func, select, update

from api.app.db.connection import get_session
from api.app.db.models import (
    Animal,
    BreedingAttempt,
    ClanMember,
    CocktailDay,
    CocktailRound,
    CocktailSolve,
    CustomAchievementRecipient,
    DailyBonus,
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
    Transfer,
    TransferClaim,
    utcnow,
)
from api.app.zoopark import ledger


def _wipe_player(session, pid: int) -> None:
    his_items = select(Item.id).where(Item.player_id == pid)
    his_sets = select(ItemSet.id).where(ItemSet.player_id == pid)
    his_expeditions = select(Expedition.id).where(Expedition.player_id == pid)

    # A shared daily row may name this player as its winner; unlink rather than delete it, so
    # other players' record of that day survives.
    session.execute(
        update(CocktailDay).where(CocktailDay.winner_player_id == pid).values(winner_player_id=None)
    )

    # Break the animals' self-references and locality links before deleting, so no parent_* or
    # locality_id foreign key blocks the delete regardless of row order.
    session.execute(
        update(Animal).where(Animal.player_id == pid).values(
            parent_a_id=None, parent_b_id=None, locality_id=None
        )
    )

    # Children before parents. Each statement is scoped to this one player.
    session.execute(delete(ExpeditionMember).where(ExpeditionMember.expedition_id.in_(his_expeditions)))
    session.execute(delete(Expedition).where(Expedition.player_id == pid))
    session.execute(delete(MerchantOffer).where(MerchantOffer.player_id == pid))
    session.execute(delete(PackOpening).where(PackOpening.player_id == pid))
    session.execute(delete(BreedingAttempt).where(BreedingAttempt.player_id == pid))
    session.execute(delete(Animal).where(Animal.player_id == pid))
    session.execute(delete(Locality).where(Locality.player_id == pid))
    session.execute(delete(ItemProperty).where(ItemProperty.item_id.in_(his_items)))
    session.execute(delete(ItemSetMember).where(ItemSetMember.item_id.in_(his_items)))
    session.execute(delete(ItemSetMember).where(ItemSetMember.set_id.in_(his_sets)))
    session.execute(delete(ItemSet).where(ItemSet.player_id == pid))
    session.execute(delete(Item).where(Item.player_id == pid))
    session.execute(delete(PlayerCosmetic).where(PlayerCosmetic.player_id == pid))
    session.execute(delete(ClanMember).where(ClanMember.player_id == pid))
    session.execute(delete(CocktailRound).where(CocktailRound.player_id == pid))
    session.execute(delete(CocktailSolve).where(CocktailSolve.player_id == pid))
    session.execute(delete(DailyBonus).where(DailyBonus.player_id == pid))
    session.execute(delete(TransferClaim).where(TransferClaim.player_id == pid))
    session.execute(delete(Transfer).where(Transfer.sender_id == pid))
    session.execute(delete(CustomAchievementRecipient).where(CustomAchievementRecipient.player_id == pid))
    session.execute(delete(NotificationOutbox).where(NotificationOutbox.player_id == pid))
    session.execute(delete(LedgerEntry).where(LedgerEntry.player_id == pid))


def reset_player(*, telegram_id: int | None, player_id: int | None, paw: int, apply: bool) -> None:
    with get_session() as session:
        if player_id is not None:
            player = session.get(Player, player_id, with_for_update=True)
        else:
            player = session.scalars(
                select(Player).where(Player.telegram_id == telegram_id).with_for_update()
            ).first()
        if player is None:
            raise SystemExit("Player not found.")

        pid = player.id
        print(
            f"Player {player.nickname!r} (id={pid}, tg={player.telegram_id}) — before: "
            f"rub={player.balance_rub} usd={player.balance_usd} paw={player.balance_paw} "
            f"animals={session.scalar(select(func.count()).select_from(Animal).where(Animal.player_id == pid))}"
        )

        _wipe_player(session, pid)

        now = utcnow()
        session.execute(
            update(Player).where(Player.id == pid).values(
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

        if paw > 0:
            session.refresh(player)
            ledger.grant(session, player, "paw", paw, "season_reset")

        total, stored = ledger.reconcile(session, pid, "paw")
        if total != stored:
            raise SystemExit(f"Ledger mismatch: ledger={total} balance={stored}. Aborting.")

        print(f"After: rub=0 usd=0 paw={stored}. Ledger reconciles.")

        if apply:
            session.commit()
            print("Applied.")
        else:
            session.rollback()
            print("Dry-run: nothing was written. Re-run with --apply to commit.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wipe one player's progress and set a PawCoin balance.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--telegram-id", type=int, help="the player's Telegram id")
    group.add_argument("--player-id", type=int, help="the player's internal id")
    parser.add_argument("--paw", type=int, default=0, help="PawCoins to credit after the wipe")
    parser.add_argument("--apply", action="store_true", help="commit (default: dry-run)")
    args = parser.parse_args()
    reset_player(
        telegram_id=args.telegram_id, player_id=args.player_id, paw=args.paw, apply=args.apply
    )
