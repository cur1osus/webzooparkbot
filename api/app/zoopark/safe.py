"""The bank safe — the only way dollars leave the treasury.

Every bank exchange feeds a commission into `treasury`, where it used to sit forever. The
safe pays part of it back out as a deduction race for a four-digit code.

Two rules carry the whole design:

* **Guesses are sealed until the window closes.** All of a day's guesses are published at
  once, with their clues. If clues appeared immediately, the player who opened the app
  last would inherit everyone else's deductions and win on timezone rather than thought.
* **A round outlives the day.** The code survives until somebody cracks it, so the
  published board grows across days. Rerolling the secret each midnight would throw away
  the only thing that makes the game skill-based.

Randomness picks the secret and nothing else; `SystemRandom`, because guessing it is
worth real money.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta
from random import SystemRandom

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import Player, SafeAttempt, SafeRound, utcnow
from api.app.schemas.games import SafeGuessBody
from api.app.zoopark import ledger
from api.app.zoopark.catalog import (
    SAFE_CODE_DIGITS,
    SAFE_CODE_LENGTH,
    SAFE_DAILY_ATTEMPTS,
    SAFE_OPEN_HOUR,
    SAFE_PRIZE_PERCENT,
    SAFE_WINDOW_HOURS,
)
from api.app.zoopark.profile import get_player
from api.app.zoopark.time import moscow_period_day, moscow_period_start, next_moscow_reset

logger = logging.getLogger(__name__)
random = SystemRandom()


# ─── Window ───────────────────────────────────────────────────────────────────


def window(now: datetime) -> tuple[date, datetime, datetime]:
    """The day currently in play and the instants its window opens and closes.

    `moscow_period_start` always returns the most recent 19:00, so `opens_at <= now` holds
    and the window is open exactly while `now < closes_at`.
    """
    opens_at = moscow_period_start(now, SAFE_OPEN_HOUR)
    return (
        moscow_period_day(now, SAFE_OPEN_HOUR),
        opens_at,
        opens_at + timedelta(hours=SAFE_WINDOW_HOURS),
    )


def is_open(now: datetime) -> bool:
    _, _, closes_at = window(now)
    return now < closes_at


def last_closed_day(now: datetime) -> date:
    """The most recent day whose guesses may already be published."""
    day, _, closes_at = window(now)
    return day if now >= closes_at else day - timedelta(days=1)


# ─── Codes ────────────────────────────────────────────────────────────────────


def new_secret() -> str:
    return "".join(random.choice(SAFE_CODE_DIGITS) for _ in range(SAFE_CODE_LENGTH))


def score(secret: str, guess: str) -> tuple[int, int]:
    """Bulls and cows. Digits repeat, so shared digits are counted as a multiset
    intersection — otherwise a guess of `1111` against `1234` would report four matches."""
    exact = sum(1 for a, b in zip(secret, guess, strict=True) if a == b)
    common = sum((Counter(secret) & Counter(guess)).values())
    return exact, common - exact


def _validate(code: str) -> str:
    code = code.strip()
    if len(code) != SAFE_CODE_LENGTH or any(ch not in SAFE_CODE_DIGITS for ch in code):
        raise HTTPException(400, f"Код — это {SAFE_CODE_LENGTH} цифры")
    return code


# ─── Rounds ───────────────────────────────────────────────────────────────────


def current_round(session: Session, now: datetime, *, create: bool = True) -> SafeRound | None:
    """The live round, creating one if the safe has never run or the last was cracked."""
    round_ = session.scalars(
        select(SafeRound).where(SafeRound.solved_at.is_(None)).order_by(SafeRound.id.desc())
    ).first()
    if round_ is not None or not create:
        return round_

    # A round cracked at tonight's reveal already holds today's `opened_on`, so the
    # replacement opens tomorrow rather than colliding with it. Without this the insert
    # fails, the recovery query hands back the *solved* round, and the safe spends the
    # night showing a code that is already public.
    last_day = session.scalar(select(func.max(SafeRound.opened_on)))
    day = moscow_period_day(now, SAFE_OPEN_HOUR)
    if last_day is not None and last_day >= day:
        day = last_day + timedelta(days=1)

    # `opened_on` is unique, so two requests racing to open the first round of a day
    # produce one. A savepoint keeps the loser from rolling back its caller.
    try:
        with session.begin_nested():
            round_ = SafeRound(secret=new_secret(), opened_on=day)
            session.add(round_)
            session.flush()
    except IntegrityError:
        # `with_for_update` is what makes this correct, not just careful. MySQL runs
        # REPEATABLE READ, so this transaction's snapshot predates the row the winner just
        # committed — a plain SELECT would find nothing even though the unique key just
        # proved the row exists, and the player would get "сейф недоступен". A locking read
        # is a current read: it sees the latest committed version.
        round_ = session.scalars(
            select(SafeRound).where(SafeRound.opened_on == day).order_by(SafeRound.id.desc()).with_for_update()
        ).first()
        if round_ is None:
            # The unique key was not what rejected the insert. Left silent, this surfaces
            # to players as an unexplained "safe unavailable" and to us as nothing at all.
            logger.exception("Safe round for %s could not be created", day)
    return round_


def _board(session: Session, round_: SafeRound, now: datetime) -> list[dict]:
    """Every guess whose window has already closed, oldest first.

    Today's sealed guesses are excluded by the `day <= last_closed_day` predicate rather
    than by a flag, so a stalled resolver cannot leak them early or hide them late.
    """
    rows = session.execute(
        select(SafeAttempt, Player.nickname)
        .join(Player, Player.id == SafeAttempt.player_id)
        .where(SafeAttempt.round_id == round_.id, SafeAttempt.day <= last_closed_day(now))
        .order_by(SafeAttempt.day.asc(), SafeAttempt.id.asc())
    ).all()
    return [
        {
            "day": attempt.day.isoformat(),
            "nickname": nickname,
            "code": attempt.code,
            "exact": attempt.exact,
            "misplaced": attempt.misplaced,
        }
        for attempt, nickname in rows
    ]


def _attempts_used(session: Session, round_id: int, player_id: int, day: date) -> int:
    return int(
        session.scalar(
            select(func.count(SafeAttempt.id)).where(
                SafeAttempt.round_id == round_id,
                SafeAttempt.player_id == player_id,
                SafeAttempt.day == day,
            )
        )
        or 0
    )


# ─── Player-facing ────────────────────────────────────────────────────────────


def has_open_attempt(tg_id: int) -> bool:
    """Whether the safe is open right now and this player still has a guess left.

    Cheap on purpose: it gates whether a rival is even shown `safe_guess`, checked once at
    the top of a turn. When the safe is shut, guessing is impossible; showing the tool only
    when a guess can be spent stops a rival from wasting a round trying while it is closed.
    """
    now = utcnow()
    if not is_open(now):
        return False
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            return False
        round_ = current_round(session, now, create=False)
        if round_ is None:
            return False
        day, _opens, _closes = window(now)
        used = _attempts_used(session, round_.id, player.id, day)
        return used < SAFE_DAILY_ATTEMPTS


def safe_state(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")

        now = utcnow()
        day, opens_at, closes_at = window(now)
        round_ = current_round(session, now)
        if round_ is None:
            raise HTTPException(503, "Сейф недоступен")

        open_now = now < closes_at
        pending = (
            session.scalars(
                select(SafeAttempt)
                .where(
                    SafeAttempt.round_id == round_.id,
                    SafeAttempt.player_id == player.id,
                    SafeAttempt.day == day,
                )
                .order_by(SafeAttempt.id.asc())
            ).all()
            if open_now
            else []
        )
        pool = ledger.treasury_balance(session, "usd")
        session.commit()
        return {
            "ok": True,
            "is_open": open_now,
            "opens_at": (opens_at if open_now else next_moscow_reset(now, SAFE_OPEN_HOUR)).isoformat(),
            "closes_at": closes_at.isoformat(),
            "code_length": SAFE_CODE_LENGTH,
            "round_day": round_.opened_on.isoformat(),
            "prize_usd": pool * SAFE_PRIZE_PERCENT // 100,
            "treasury_usd": pool,
            "attempts_left": max(0, SAFE_DAILY_ATTEMPTS - len(pending)),
            # The player's own sealed guesses, without clues: they are scored on
            # submission, but publishing the clue now would defeat the sealed window.
            "pending_codes": [attempt.code for attempt in pending],
            "board": _board(session, round_, now),
        }


def safe_guess(tg_id: int, body: SafeGuessBody) -> dict:
    code = _validate(body.code)

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        now = utcnow()
        day, _, closes_at = window(now)
        if now >= closes_at:
            raise HTTPException(400, "Сейф закрыт, приходи завтра в 19:00")

        round_ = current_round(session, now)
        if round_ is None:
            raise HTTPException(503, "Сейф недоступен")

        used = _attempts_used(session, round_.id, player.id, day)
        if used >= SAFE_DAILY_ATTEMPTS:
            raise HTTPException(400, "Попытки на сегодня закончились")

        exact, misplaced = score(round_.secret, code)
        session.add(
            SafeAttempt(
                round_id=round_.id,
                player_id=player.id,
                day=day,
                code=code,
                exact=exact,
                misplaced=misplaced,
            )
        )
        session.commit()
        # The clue is deliberately absent from the response — the player learns it at
        # 23:00 together with everyone else.
        return {
            "ok": True,
            "accepted": code,
            "attempts_left": max(0, SAFE_DAILY_ATTEMPTS - used - 1),
            "closes_at": closes_at.isoformat(),
        }


# ─── Resolution ───────────────────────────────────────────────────────────────


def resolve_due_days(session: Session, now: datetime | None = None) -> dict | None:
    """Publish every closed day the resolver has not seen yet and pay the first crack.

    Returns the payout when a round ends, otherwise `None`. Idempotent through
    `resolved_day`: a worker that dies mid-payout resumes at the day it had not marked,
    and days already marked are never paid twice.
    """
    now = now or utcnow()
    round_ = session.scalars(
        select(SafeRound).where(SafeRound.solved_at.is_(None)).order_by(SafeRound.id.desc()).with_for_update()
    ).first()
    if round_ is None:
        return None

    horizon = last_closed_day(now)
    days = session.scalars(
        select(SafeAttempt.day)
        .where(
            SafeAttempt.round_id == round_.id,
            SafeAttempt.day <= horizon,
            *([SafeAttempt.day > round_.resolved_day] if round_.resolved_day else []),
        )
        .distinct()
        .order_by(SafeAttempt.day.asc())
    ).all()

    for day in days:
        round_.resolved_day = day
        winner_ids = session.scalars(
            select(SafeAttempt.player_id)
            .where(
                SafeAttempt.round_id == round_.id,
                SafeAttempt.day == day,
                SafeAttempt.exact == SAFE_CODE_LENGTH,
            )
            .distinct()
        ).all()
        if not winner_ids:
            continue
        return _pay_out(session, round_, day, sorted(winner_ids), now)
    return None


def _pay_out(session: Session, round_: SafeRound, day: date, winner_ids: list[int], now: datetime) -> dict:
    """Split half the treasury between everyone who named the code that day.

    Ties split evenly rather than going to whoever submitted first: guesses are sealed, so
    submission order is an accident of when the app happened to be open.
    """
    pool = ledger.treasury_balance(session, "usd")
    share = (pool * SAFE_PRIZE_PERCENT // 100) // len(winner_ids)

    payouts: list[dict] = []
    granted = 0
    for player_id in winner_ids:
        winner = session.get(Player, player_id, with_for_update=True)
        if winner is None:
            continue
        # Debit first and credit exactly what came out: an exchange committing between the
        # read above and this line must not let the safe pay money the treasury lacks.
        taken = ledger.debit_treasury(
            session, "usd", share, "safe_prize", ref_table="safe_rounds", ref_id=round_.id
        )
        if taken <= 0:
            break
        ledger.grant(session, winner, "usd", taken, "safe_prize")
        granted += taken
        payouts.append({"player_id": winner.id, "nickname": winner.nickname, "usd": taken})

    round_.solved_at = now
    round_.prize_usd = granted
    session.flush()
    logger.info("Safe round %s cracked on %s: $%s to %s", round_.id, day, granted, len(payouts))
    return {"round_id": round_.id, "day": day, "secret": round_.secret, "payouts": payouts, "prize_usd": granted}
