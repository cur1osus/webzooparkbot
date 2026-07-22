"""The cocktail puzzle and Telegram Stars.

Duels and solo games used to live here too. Both were removed on 2026-07-22: they staked
currency the idle loop already prints, so risking it was never worth it, and the duel
lobby needed a second live player inside a ten-minute window that a population of this
size cannot supply. What is left are the two games that ask for a guess rather than a bet.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from random import SystemRandom

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.core.telegram import TelegramApiError, call_bot_api
from api.app.db.connection import get_session
from api.app.db.models import CocktailDay, CocktailRound, CocktailSolve, Player, StarPayment, utcnow
from api.app.schemas.games import CocktailGuessBody, DonateInvoiceBody
from api.app.zoopark import ledger
from api.app.zoopark.catalog import (
    COCKTAIL_BASE_ATTEMPTS,
    COCKTAIL_FIRST_SOLVER_MULTIPLIER,
    COCKTAIL_FRUITS,
    COCKTAIL_LENGTH,
    COCKTAIL_REWARD_PAW,
    STARS_TO_PAW,
)
from api.app.zoopark.profile import get_player
from api.app.zoopark.time import moscow_period_day, next_moscow_reset

logger = logging.getLogger(__name__)
random = SystemRandom()
COCKTAIL_RESET_HOUR = 10


# ─── Telegram Stars ───────────────────────────────────────────────────────────


def donate_info() -> dict:
    return {"stars_to_paw": STARS_TO_PAW}


def donate_invoice(tg_id: int, body: DonateInvoiceBody) -> dict:
    try:
        data = call_bot_api(
            "createInvoiceLink",
            {
                "title": f"Донат {body.stars} ⭐️",
                "description": f"Получи {body.stars * STARS_TO_PAW} 🐾 PawCoins",
                # The webhook never trusts this payload: it credits the payer named by
                # Telegram, in the amount Telegram actually charged.
                "payload": f"donate_{tg_id}_{body.stars}",
                "currency": "XTR",
                "prices": [{"label": "Stars", "amount": body.stars}],
            },
        )
    except TelegramApiError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"invoice_link": data["result"]}


def credit_star_payment(telegram_id: int, charge_id: str, stars: int) -> bool:
    """Idempotent by `charge_id`, which is the primary key of `star_payments`."""
    if stars < 1 or not charge_id:
        logger.warning("Ignoring malformed payment charge_id=%r stars=%r", charge_id, stars)
        return False

    paw = stars * STARS_TO_PAW
    with get_session() as session:
        if session.get(StarPayment, charge_id):
            logger.info("Payment %s already credited", charge_id)
            return False

        player = get_player(session, telegram_id, for_update=True)
        if not player:
            logger.error("Payment %s from unknown player %s", charge_id, telegram_id)
            return False

        session.add(
            StarPayment(charge_id=charge_id, player_id=player.id, stars=stars, paw_credited=paw)
        )
        ledger.grant(session, player, "paw", paw, "star_payment", ref_table="star_payments")
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            logger.info("Payment %s credited concurrently", charge_id)
            return False

    logger.info("Credited %s PawCoins to %s for payment %s", paw, telegram_id, charge_id)
    return True


def refund_star_payment(charge_id: str) -> bool:
    """Telegram refunded the Stars, so the PawCoins go back too.

    Without this a player could buy 1 000 PawCoins, ask Telegram for their money back and
    keep both. The balance may already have been spent, in which case it goes to zero and
    the shortfall is logged: the ledger will show exactly what was taken.
    """
    if not charge_id:
        return False

    with get_session() as session:
        payment = session.get(StarPayment, charge_id, with_for_update=True)
        if payment is None:
            logger.warning("Refund for unknown payment %s", charge_id)
            return False
        if payment.refunded_at is not None:
            return False

        player = session.get(Player, payment.player_id, with_for_update=True)
        if player is None:
            return False

        available = ledger.balance(player, "paw")
        clawed_back = min(available, int(payment.paw_credited))
        if clawed_back < payment.paw_credited:
            logger.warning(
                "Refund %s claws back only %s of %s PawCoins from player %s",
                charge_id, clawed_back, payment.paw_credited, player.id,
            )
        if clawed_back:
            ledger.spend(session, player, "paw", clawed_back, "star_refund", ref_table="star_payments")
        payment.refunded_at = utcnow()
        session.commit()

    logger.info("Refunded payment %s", charge_id)
    return True


# ─── Cocktail ─────────────────────────────────────────────────────────────────


def _cocktail_period(now: datetime) -> tuple[date, datetime]:
    """Return the cocktail period key and its next reset at 10:00 Moscow time."""
    return (
        moscow_period_day(now, COCKTAIL_RESET_HOUR),
        next_moscow_reset(now, COCKTAIL_RESET_HOUR),
    )


def _cocktail_history(round_: CocktailRound) -> list[dict]:
    try:
        history = json.loads(round_.history or "[]")
    except (TypeError, ValueError):
        return []
    return history if isinstance(history, list) else []


def _get_cocktail_day(session: Session, now: datetime) -> CocktailDay:
    day, _ = _cocktail_period(now)
    daily = session.scalars(
        select(CocktailDay).where(CocktailDay.day == day).with_for_update()
    ).first()
    if daily is not None:
        return daily

    # The first guess of the day creates the shared recipe. A savepoint keeps a
    # concurrent insert from rolling back the player's locked transaction.
    try:
        with session.begin_nested():
            daily = CocktailDay(
                day=day,
                secret=json.dumps(random.sample(COCKTAIL_FRUITS, COCKTAIL_LENGTH)),
            )
            session.add(daily)
            session.flush()
    except IntegrityError:
        daily = None

    if daily is None:
        daily = session.scalars(
            select(CocktailDay).where(CocktailDay.day == day).with_for_update()
        ).first()
    if daily is None:
        raise HTTPException(503, "Не удалось открыть коктейль дня")
    return daily


def _solved_today(session: Session, day: date) -> int:
    """How many players have cracked today's recipe — the board everyone is measured against."""
    return int(session.scalar(select(func.count()).select_from(CocktailSolve).where(CocktailSolve.day == day)) or 0)


def cocktail_state(tg_id: int) -> dict:
    """Return the current player's persisted cocktail board."""
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")

        now = utcnow()
        day, _ = _cocktail_period(now)
        # A separate name: `day` is the date the period falls on, and the row keyed by it is
        # a different thing. Writing the row back over the date made `winner_player_id` look
        # like an attribute of `date`.
        cocktail_day = session.scalars(select(CocktailDay).where(CocktailDay.day == day)).first()
        round_ = session.get(CocktailRound, player.id)
        current_round = round_ if round_ is not None and round_.expires_at > now else None
        history = _cocktail_history(current_round) if current_round else []
        solved = bool(current_round and current_round.solved_at is not None)
        winner_id = cocktail_day.winner_player_id if cocktail_day else None
        winner = session.get(Player, winner_id) if winner_id else None
        return {
            "ok": True,
            "attempts_left": max(0, COCKTAIL_BASE_ATTEMPTS - (current_round.attempts if current_round else 0)),
            "history": history,
            "solved": solved,
            # Solving is being paid, so the two say the same thing now. `rewarded` stays in
            # the payload because the client reads it to show the reward line.
            "rewarded": solved,
            "was_first": winner_id == player.id,
            "winner_nickname": winner.nickname if winner else None,
            "solved_today": _solved_today(session, day),
        }


def cocktail_guess(tg_id: int, body: CocktailGuessBody) -> dict:
    fruits = body.fruits
    if len(fruits) != COCKTAIL_LENGTH:
        raise HTTPException(400, f"Нужно {COCKTAIL_LENGTH} фрукта")
    if any(fruit not in COCKTAIL_FRUITS for fruit in fruits):
        raise HTTPException(400, "Неизвестный фрукт")

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        now = utcnow()
        daily = _get_cocktail_day(session, now)
        round_ = session.get(CocktailRound, player.id, with_for_update=True)

        # The round resets at the next 10:00 Moscow time, not 24 hours after it started: a
        # player who solved it a minute in should not wait 23 hours and 59 minutes.
        if round_ is None or round_.expires_at <= now or round_.secret != daily.secret:
            _, next_reset = _cocktail_period(now)
            if round_ is None:
                round_ = CocktailRound(
                    player_id=player.id,
                    secret=daily.secret,
                    history="[]",
                    expires_at=next_reset,
                )
                session.add(round_)
            else:
                round_.secret = daily.secret
                round_.attempts = 0
                round_.history = "[]"
                round_.solved_at = None
                round_.started_at = now
                round_.expires_at = next_reset
            session.flush()

        if round_.solved_at is not None:
            raise HTTPException(400, "Коктейль уже разгадан, приходи завтра")

        max_attempts = COCKTAIL_BASE_ATTEMPTS
        if round_.attempts >= max_attempts:
            raise HTTPException(400, "Попытки закончились, приходи завтра")

        secret = json.loads(round_.secret)
        round_.attempts += 1

        clues = []
        for index, fruit in enumerate(fruits):
            if fruit == secret[index]:
                clues.append({"pos": index, "status": "correct"})
            elif fruit in secret:
                clues.append({"pos": index, "status": "present"})
            else:
                clues.append({"pos": index, "status": "absent"})

        won = all(clue["status"] == "correct" for clue in clues)
        history = _cocktail_history(round_)
        history.append({"fruits": fruits, "clues": clues})
        round_.history = json.dumps(history, ensure_ascii=False)
        result: dict = {
            "ok": True,
            "won": won,
            "attempts_left": max(0, max_attempts - round_.attempts),
            "clues": clues,
        }
        if won:
            round_.solved_at = now
            # Every solver is paid. `winner_player_id` now records only who got there first,
            # which is what the double reward and the name on the board are for.
            is_first = daily.winner_player_id is None
            if is_first:
                daily.winner_player_id = player.id
            reward = COCKTAIL_REWARD_PAW * (COCKTAIL_FIRST_SOLVER_MULTIPLIER if is_first else 1)
            # The unique key on (player_id, day) is what actually stops a double payout: the
            # `solved_at` check above guards the common path, but the round row is rewritten
            # whenever the day rolls over, so it cannot speak for a day that already paid.
            session.add(
                CocktailSolve(
                    player_id=player.id,
                    day=daily.day,
                    attempts=round_.attempts,
                    was_first=is_first,
                    reward_paw=reward,
                    created_at=now,
                )
            )
            try:
                session.flush()
            except IntegrityError as err:
                # The unique index did the deciding, not this check — two tabs racing the same
                # last guess land here, and only one of them gets the reward.
                raise HTTPException(400, "Коктейль уже разгадан, приходи завтра") from err
            ledger.grant(session, player, "paw", reward, "cocktail_reward")
            result["reward_paw"] = reward
            result["was_first"] = is_first
            result["new_paw_coins"] = ledger.balance(player, "paw")

        winner = session.get(Player, daily.winner_player_id) if daily.winner_player_id else None
        result["winner_nickname"] = winner.nickname if winner else None
        result["solved_today"] = _solved_today(session, daily.day)

        session.commit()
        return result
