"""Create (or refresh) the AI rival players and their profiles. Idempotent.

    python -m api.scripts.create_bots            # create anything missing
    python -m api.scripts.create_bots --list     # show what exists

A rival registers through `core.register`, exactly as a human does, so it gets the same
starting grant, the same season and the same first locality — nothing is hand-seeded into its
row. Its `telegram_id` is the negative of a small ordinal; real Telegram ids are positive, so
the two can never collide, and the negative value cannot authenticate through
`parse_tg_id` either (initData is signed by Telegram, and DEV_AUTH is off in production).
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.app.db.connection import get_session
from api.app.db.models import BotProfile, Player, utcnow
from api.app.schemas.core import RegisterBody
from api.app.zoopark import core as core_service
from api.app.zoopark.core import PROFILE_ACHIEVEMENT_PREFIX
from api.bots.characters import CHARACTERS

# Ordinal → negative telegram id. Stable, so re-running finds the same rows.
BOT_TELEGRAM_IDS = {"gambler": -1002}

# Rivals that once existed and no longer should. Retired rather than deleted: the account
# holds ledger entries, and the ledger is a closed system whose totals must keep adding up.
# `--retire` disables its turns and drops it out of the active leaderboard; nothing is lost,
# and putting it back is two column updates.
RETIRED_TELEGRAM_IDS = {-1001: "hoarder (Бьёрн)"}


def _find(tg_id: int) -> int | None:
    """Player id, read in a session of its own.

    Registration commits in its *own* session, and MySQL defaults to REPEATABLE READ — a
    session opened before that commit keeps its snapshot and will not see the new row no
    matter how many times it re-queries. So each step here gets a fresh session.
    """
    with get_session() as session:
        player = session.scalar(select(Player).where(Player.telegram_id == tg_id))
        return player.id if player else None


def create_all() -> None:
    for key, character in CHARACTERS.items():
        tg_id = BOT_TELEGRAM_IDS[key]

        player_id = _find(tg_id)
        if player_id is None:
            core_service.register(tg_id, RegisterBody(nickname=character.nickname))
            player_id = _find(tg_id)
            if player_id is None:
                print(f"  ✗ {character.nickname}: регистрация не создала игрока", file=sys.stderr)
                continue
            print(f"  + игрок {character.nickname} (tg_id={tg_id}, id={player_id})")
        else:
            print(f"  = игрок {character.nickname} уже есть (id={player_id})")

        with get_session() as session:
            player = session.get(Player, player_id)
            player.is_bot = True

            # Renames an existing rival when its character is given a new name, so this
            # script stays the one place a bot's identity is defined.
            if player.nickname != character.nickname:
                previous = player.nickname
                try:
                    player.nickname = character.nickname
                    session.flush()
                except IntegrityError:
                    session.rollback()
                    player = session.get(Player, player_id)
                    print(f"  ! {previous}: имя «{character.nickname}» уже занято, оставляю как есть",
                          file=sys.stderr)
                else:
                    print(f"  ~ переименован: {previous} → {character.nickname}")

            # A raw glyph here would make the rival the only account in the game rendering
            # as a bare character. NULL gives it the same default animal a new player gets;
            # a real avatar is earned later by unlocking an achievement and wearing it.
            if player.profile_emoji and not player.profile_emoji.startswith(PROFILE_ACHIEVEMENT_PREFIX):
                print(f"  ~ снят кастомный аватар «{player.profile_emoji}» → животное по умолчанию")
                player.profile_emoji = None

            profile = session.get(BotProfile, player.id)
            if profile is None:
                session.add(
                    BotProfile(
                        player_id=player.id,
                        character=key,
                        enabled=True,
                        turn_every_minutes=character.turn_every_minutes,
                        wake_hour_utc=character.wake_hour_utc,
                        sleep_hour_utc=character.sleep_hour_utc,
                        biography="",
                        created_at=utcnow(),
                    )
                )
                print(f"  + профиль {key}: ход каждые {character.turn_every_minutes} мин, "
                      f"бодрствует {character.wake_hour_utc}:00-{character.sleep_hour_utc}:00 UTC")
            else:
                print(f"  = профиль {key} уже есть (enabled={profile.enabled})")
            session.commit()


def list_all() -> None:
    with get_session() as session:
        rows = session.execute(
            select(Player, BotProfile).join(BotProfile, BotProfile.player_id == Player.id)
        ).all()
        if not rows:
            print("ботов нет")
            return
        for player, profile in rows:
            print(
                f"{player.profile_emoji or '?'} {player.nickname:16} character={profile.character:10} "
                f"enabled={profile.enabled} доход={player.income_rub_per_min} "
                f"баланс={player.balance_rub} след.план={profile.next_plan_at}"
            )


def retire_removed() -> None:
    """Stop rivals that are no longer part of the roster, without destroying their rows."""
    for tg_id, label in RETIRED_TELEGRAM_IDS.items():
        player_id = _find(tg_id)
        if player_id is None:
            continue
        with get_session() as session:
            player = session.get(Player, player_id)
            profile = session.get(BotProfile, player_id)
            if profile is not None:
                profile.enabled = False
                profile.next_turn_at = None
            # `banned` is the game's only non-active status, and the leaderboard and player
            # lists already filter on it — so this removes the retired rival from view
            # without deleting an account whose ledger entries have to keep balancing.
            if player is not None and player.status == "active":
                player.status = "banned"
            session.commit()
        print(f"  − выведен из игры: {label}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the AI rivals")
    parser.add_argument("--list", action="store_true", help="show existing bots and exit")
    args = parser.parse_args()
    if args.list:
        list_all()
        return
    create_all()
    retire_removed()


if __name__ == "__main__":
    main()
