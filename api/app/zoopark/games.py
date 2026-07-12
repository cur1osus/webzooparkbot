"""Duels, solo games, the cocktail puzzle and Telegram Stars.

Duels are player-versus-player and zero-sum, so the `duel_moves` and `duel_bonus` item
properties apply there. Solo games are against the house, whose 4% edge is the only thing
draining rubles out of the casino — no item touches them.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from random import SystemRandom

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.core.telegram import TelegramApiError, call_bot_api
from api.app.db.connection import get_session
from api.app.db.models import CocktailRound, Duel, Player, SoloStats, StarPayment, utcnow
from api.app.schemas.games import CocktailGuessBody, DonateInvoiceBody, DuelCreateBody, SoloStartBody
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import ledger
from api.app.zoopark.catalog import (
    COCKTAIL_BASE_ATTEMPTS,
    COCKTAIL_FRUITS,
    COCKTAIL_LENGTH,
    COCKTAIL_REWARD_PAW,
    DUEL_BASE_MOVES,
    DUEL_DICE_SIDES,
    GAME_KINDS,
    MAX_STAKE_RUB,
    SOLO_MATCH_MAX_ROUNDS,
    SOLO_MATCH_MIN_ROUNDS,
    SOLO_WIN_CHANCE_PCT,
    STARS_TO_PAW,
)
from api.app.zoopark.income import sync_player_income
from api.app.zoopark.profile import get_player

logger = logging.getLogger(__name__)
random = SystemRandom()


def _validate_stake(value: int) -> int:
    if value <= 0:
        raise HTTPException(400, "Ставка должна быть больше нуля")
    if value > MAX_STAKE_RUB:
        raise HTTPException(400, "Слишком крупная ставка")
    return value


def _validate_kind(kind: str) -> str:
    if kind not in GAME_KINDS:
        raise HTTPException(400, "Неизвестный тип игры")
    return kind


# ─── Duels ────────────────────────────────────────────────────────────────────


def _lock_players(session: Session, *player_ids: int) -> dict[int, Player]:
    """Locked in a stable order, so two joins can never deadlock each other."""
    ordered = sorted(set(player_ids))
    rows = session.scalars(
        select(Player).where(Player.id.in_(ordered)).order_by(Player.id.asc()).with_for_update()
    ).all()
    return {row.id: row for row in rows}


def _duel_payload(session: Session, duel: Duel) -> dict:
    creator = session.get(Player, duel.creator_id)
    winner = session.get(Player, duel.winner_id) if duel.winner_id else None
    return {
        "id": duel.id,
        "kind": duel.kind,
        "stake_rub": int(duel.stake_rub),
        "creator_nickname": creator.nickname if creator else "—",
        "created_at": duel.created_at.isoformat(),
        "status": duel.status,
        "creator_score": duel.creator_score,
        "opponent_score": duel.opponent_score,
        "winner_nickname": winner.nickname if winner else None,
    }


def open_duels() -> dict:
    with get_session() as session:
        duels = session.scalars(
            select(Duel).where(Duel.status == "open").order_by(Duel.created_at.desc()).limit(20)
        ).all()
        return {"games": [_duel_payload(session, duel) for duel in duels]}


def create_duel(tg_id: int, body: DuelCreateBody) -> dict:
    stake = _validate_stake(body.stake_rub)
    kind = _validate_kind(body.kind)

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)

        duel = Duel(kind=kind, stake_rub=stake, creator_id=player.id, status="open")
        session.add(duel)
        session.flush()
        ledger.spend(session, player, "rub", stake, "duel_stake", ref_table="duels", ref_id=duel.id)

        payload = _duel_payload(session, duel)
        result = {"ok": True, "game": payload, "new_rub": ledger.balance(player, "rub")}
        session.commit()
        return result


def _roll_score(session: Session, player_id: int) -> int:
    """`DUEL_BASE_MOVES` dice plus whatever the player's active items add."""
    bonuses = bonuses_module.load(session, player_id)
    moves = DUEL_BASE_MOVES + bonuses.total("duel_moves")
    score = sum(random.randint(1, DUEL_DICE_SIDES) for _ in range(moves))
    return score + bonuses.total("duel_bonus")


def join_duel(tg_id: int, duel_id: int) -> dict:
    with get_session() as session:
        joiner = get_player(session, tg_id)
        if not joiner:
            raise HTTPException(404, "Нет игрока")
        joiner_id = joiner.id

        # Lock the duel first, then both players: without this two clients could each pass
        # the `status == "open"` check and each collect the doubled pot.
        duel = session.scalars(select(Duel).where(Duel.id == duel_id).with_for_update()).first()
        if not duel:
            raise HTTPException(404, "Игра не найдена")
        if duel.status != "open":
            raise HTTPException(400, "Игра недоступна")
        if duel.creator_id == joiner_id:
            raise HTTPException(400, "Нельзя вступить в свою игру")

        players = _lock_players(session, duel.creator_id, joiner_id)
        creator = players.get(duel.creator_id)
        joiner = players.get(joiner_id)
        if creator is None or joiner is None:
            raise HTTPException(404, "Игрок не найден")
        sync_player_income(session, joiner)

        stake = int(duel.stake_rub)
        ledger.spend(session, joiner, "rub", stake, "duel_stake", ref_table="duels", ref_id=duel.id)

        creator_score = _roll_score(session, creator.id)
        opponent_score = _roll_score(session, joiner.id)
        while creator_score == opponent_score:
            creator_score = _roll_score(session, creator.id)
            opponent_score = _roll_score(session, joiner.id)

        winner = creator if creator_score > opponent_score else joiner
        duel.opponent_id = joiner_id
        duel.status = "finished"
        duel.creator_score = creator_score
        duel.opponent_score = opponent_score
        duel.winner_id = winner.id
        duel.resolved_at = utcnow()

        ledger.grant(session, winner, "rub", stake * 2, "duel_payout", ref_table="duels", ref_id=duel.id)

        payload = _duel_payload(session, duel)
        result = {"ok": True, "game": payload, "new_rub": ledger.balance(joiner, "rub")}
        session.commit()
        return result


def cancel_duel(tg_id: int, duel_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        duel = session.scalars(select(Duel).where(Duel.id == duel_id).with_for_update()).first()
        if not duel:
            raise HTTPException(404, "Игра не найдена")
        if duel.creator_id != player.id:
            raise HTTPException(403, "Это не твоя игра")
        if duel.status != "open":
            raise HTTPException(400, "Игру уже нельзя отменить")

        duel.status = "cancelled"
        duel.resolved_at = utcnow()
        refunded = int(duel.stake_rub)
        ledger.grant(session, player, "rub", refunded, "duel_refund", ref_table="duels", ref_id=duel.id)

        result = {"ok": True, "refunded_rub": refunded, "new_rub": ledger.balance(player, "rub")}
        session.commit()
        return result


def get_duel(duel_id: int) -> dict:
    with get_session() as session:
        duel = session.get(Duel, duel_id)
        if not duel:
            raise HTTPException(404, "Игра не найдена")
        return {"ok": True, "game": _duel_payload(session, duel)}


# ─── Solo games ───────────────────────────────────────────────────────────────


def _solo_roll_bounds(kind: str) -> tuple[int, int]:
    return (1, 5) if kind in {"basketball", "football"} else (1, 6)


def _solo_roll_score(kind: str, roll: int) -> int:
    if kind == "basketball":
        return 2 if roll >= 3 else 0
    if kind == "football":
        return 1 if roll >= 3 else 0
    return roll


def simulate_solo_match(kind: str) -> tuple[list[dict[str, int]], int, int]:
    history: list[dict[str, int]] = []
    player_score = 0
    ai_score = 0
    round_no = 1
    low, high = _solo_roll_bounds(kind)
    target_rounds = random.randint(SOLO_MATCH_MIN_ROUNDS, SOLO_MATCH_MAX_ROUNDS)

    while round_no <= target_rounds or player_score == ai_score:
        player_roll = random.randint(low, high)
        ai_roll = random.randint(low, high)
        player_score += _solo_roll_score(kind, player_roll)
        ai_score += _solo_roll_score(kind, ai_roll)
        history.append({"round": round_no, "player_roll": player_roll, "ai_roll": ai_roll})
        round_no += 1

    return history, player_score, ai_score


def start_solo_game(tg_id: int, body: SoloStartBody) -> dict:
    stake = _validate_stake(body.stake_rub)
    kind = _validate_kind(body.kind)

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)

        # The stake leaves the balance first, so an insufficient balance fails before the
        # dice are rolled rather than after.
        ledger.spend(session, player, "rub", stake, "solo_stake")

        won = random.randint(1, 100) <= SOLO_WIN_CHANCE_PCT
        while True:
            history, player_score, ai_score = simulate_solo_match(kind)
            if (player_score > ai_score) == won:
                break

        if won:
            ledger.grant(session, player, "rub", stake * 2, "solo_payout")

        stats = session.get(SoloStats, player.id, with_for_update=True)
        if stats is None:
            stats = SoloStats(player_id=player.id)
            session.add(stats)
            session.flush()
        stats.games_played += 1
        stats.wins += 1 if won else 0
        stats.losses += 0 if won else 1
        stats.won_rub += stake if won else 0
        stats.lost_rub += 0 if won else stake

        result = {
            "ok": True,
            "won": won,
            "rub_delta": stake if won else -stake,
            "new_rub": ledger.balance(player, "rub"),
            "history": history,
            "player_score": player_score,
            "ai_score": ai_score,
            "result": f"Счёт: {player_score} — {ai_score}",
        }
        session.commit()
        return result


def solo_stats(tg_id: int) -> dict:
    empty = {"games_played": 0, "wins": 0, "losses": 0, "won_rub": 0, "lost_rub": 0}
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            return empty
        stats = session.get(SoloStats, player.id)
        if not stats:
            return empty
        return {
            "games_played": stats.games_played,
            "wins": stats.wins,
            "losses": stats.losses,
            "won_rub": stats.won_rub,
            "lost_rub": stats.lost_rub,
        }


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


def _next_utc_midnight(now: datetime) -> datetime:
    start = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return start + timedelta(days=1)


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
        round_ = session.get(CocktailRound, player.id, with_for_update=True)

        # The round resets at the next UTC midnight, not 24 hours after it started: a
        # player who solved it a minute in should not wait 23 hours and 59 minutes.
        if round_ is None or round_.expires_at <= now:
            secret = random.sample(COCKTAIL_FRUITS, COCKTAIL_LENGTH)
            if round_ is None:
                round_ = CocktailRound(player_id=player.id, secret=json.dumps(secret), expires_at=_next_utc_midnight(now))
                session.add(round_)
            else:
                round_.secret = json.dumps(secret)
                round_.attempts = 0
                round_.solved_at = None
                round_.started_at = now
                round_.expires_at = _next_utc_midnight(now)
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
        result: dict = {
            "ok": True,
            "won": won,
            "attempts_left": max(0, max_attempts - round_.attempts),
            "clues": clues,
        }
        if won:
            round_.solved_at = now
            ledger.grant(session, player, "paw", COCKTAIL_REWARD_PAW, "cocktail_reward")
            result["reward_paw"] = COCKTAIL_REWARD_PAW
            result["new_paw_coins"] = ledger.balance(player, "paw")

        session.commit()
        return result
