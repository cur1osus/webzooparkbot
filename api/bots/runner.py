"""The loop that wakes the AI rivals and lets them take a turn.

Runs as its own process (`webzooparkbot-bots`), not as a thread inside the API: it can be
restarted, tailed and switched off without touching the game, a turn blocks for minutes
against a reasoning model, and `--once --dry-run` gives a way to watch a rival play without
letting it act.

Each bot is claimed with `SELECT ... FOR UPDATE SKIP LOCKED` plus a `locked_at` stamp, the
same shape the notification outbox uses — not because two runners are expected, but because
the failure mode of an accidental second one is a rival spending its money twice.

Sessions are short and never held across a turn. The tools each open their own session and
take `SELECT ... FOR UPDATE` on the player row; a transaction held open here would deadlock
against them on MySQL.

    python -m api.bots.runner                  # the service
    python -m api.bots.runner --once           # one pass, then exit
    python -m api.bots.runner --once --dry-run # read-only tools only, changes nothing
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import threading
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import BotPlan, BotProfile, Player, utcnow
from api.bots import agent, characters, memory_store

logger = logging.getLogger(__name__)

POLL_SECONDS = 60.0
# A claim older than this is treated as abandoned — a runner that died mid-turn must not
# leave a rival frozen forever. Longer than the agent deadline, or a slow turn would be
# reclaimed while it is still running.
STALE_CLAIM = timedelta(minutes=20)


def _awake(profile: BotProfile, hour_utc: int) -> bool:
    wake, sleep = profile.wake_hour_utc, profile.sleep_hour_utc
    if wake == sleep:
        return True
    if wake < sleep:
        return wake <= hour_utc < sleep
    return hour_utc >= wake or hour_utc < sleep  # window wraps past midnight


def _claim(session: Session, now) -> list[int]:
    stale_before = now - STALE_CLAIM
    profiles = session.scalars(
        select(BotProfile).where(BotProfile.enabled.is_(True)).with_for_update(skip_locked=True)
    ).all()
    claimed = []
    for profile in profiles:
        if profile.locked_at is not None and profile.locked_at > stale_before:
            continue
        profile.locked_at = now
        claimed.append(profile.player_id)
    return claimed


def _release(player_id: int) -> None:
    with get_session() as session:
        profile = session.get(BotProfile, player_id)
        if profile is not None:
            profile.locked_at = None
        session.commit()


def _process(player_id: int, now, *, dry_run: bool) -> bool:
    with get_session() as session:
        profile = session.get(BotProfile, player_id)
        player = session.get(Player, player_id)
        if profile is None or player is None or player.status != "active":
            return False
        if not dry_run and not _awake(profile, now.hour):
            return False
        if not dry_run and profile.next_turn_at is not None and profile.next_turn_at > now:
            return False

        character = characters.get(profile.character)
        tg_id = int(player.telegram_id)
        nickname = player.nickname
        turn_every = profile.turn_every_minutes
        session.commit()

    # No session is open from here on: the model call takes minutes, and every tool the
    # model reaches for opens its own.
    result = agent.run_turn(character, tg_id, player_id, nickname, dry_run=dry_run)

    if dry_run:
        _print_turn(nickname, character, result)
        return True

    with get_session() as session:
        session.add(BotPlan(
            player_id=player_id,
            character=character.key,
            rounds=result.rounds,
            tool_calls=json.dumps(result.tool_calls, ensure_ascii=False, default=str),
            summary=result.summary,
            stopped_because=result.stopped_because,
            prompt_tokens=result.prompt_tokens,
            cached_tokens=result.cached_tokens,
            completion_tokens=result.completion_tokens,
            reasoning_tokens=result.reasoning_tokens,
            cost_micro_rub=result.cost_micro_rub,
        ))
        profile = session.get(BotProfile, player_id)
        profile.next_turn_at = now + timedelta(minutes=turn_every)
        session.commit()
    return True


def _print_turn(nickname: str, character, result: agent.TurnResult) -> None:
    print(f"\n  {nickname} [{character.key}]")
    print(f"  кругов: {result.rounds}, вызовов: {len(result.tool_calls)}, "
          f"остановился: {result.stopped_because}")
    for call in result.tool_calls:
        output = call["результат"]
        mark = "✓" if output.get("ok", True) else "✗"
        detail = "" if output.get("ok", True) else f" — {output.get('error')}"
        args = json.dumps(call["аргументы"], ensure_ascii=False) if call["аргументы"] else ""
        print(f"    {mark} {call['name']}{args}{detail}")
    if result.summary:
        print(f"  итог: {result.summary}")
    print(f"  токены: {result.prompt_tokens} вх (из кэша {result.cached_tokens}) / "
          f"{result.completion_tokens} вых → {result.cost_micro_rub / 1e6:.4f} ₽")


def tick(*, dry_run: bool = False) -> int:
    now = utcnow()
    with get_session() as session:
        claimed = _claim(session, now)
        if not dry_run:
            session.commit()

    touched = 0
    for player_id in claimed:
        try:
            if _process(player_id, now, dry_run=dry_run):
                touched += 1
        except Exception:  # noqa: BLE001 — one bad rival must not stop the others
            logger.exception("bot %s failed this tick", player_id)
        finally:
            if not dry_run:
                _release(player_id)
    return touched


class BotRunner:
    def __init__(self, *, poll_seconds: float = POLL_SECONDS) -> None:
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()

    def stop(self, *_) -> None:
        self._stop.set()

    def run(self) -> None:
        logger.info("bot runner started, polling every %.0fs", self.poll_seconds)
        while not self._stop.is_set():
            try:
                tick()
            except Exception:  # noqa: BLE001
                logger.exception("bot runner iteration failed")
            self._stop.wait(self.poll_seconds)
        logger.info("bot runner stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI rivals")
    parser.add_argument("--once", action="store_true", help="one pass, then exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="only read-only tools are executed; nothing is written or spent")
    parser.add_argument("--memory-dir", help="override where bot notes are stored")
    parser.add_argument("--poll-seconds", type=float, default=POLL_SECONDS)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.memory_dir:
        memory_store.MEMORY_DIR = memory_store.Path(args.memory_dir)

    if args.dry_run:
        print(f"\nпросмотрено ботов: {tick(dry_run=True)} (изменений не вносилось)")
        return
    if args.once:
        print(f"обработано ботов: {tick()}")
        return

    runner = BotRunner(poll_seconds=args.poll_seconds)
    signal.signal(signal.SIGTERM, runner.stop)
    signal.signal(signal.SIGINT, runner.stop)
    runner.run()


if __name__ == "__main__":
    main()
