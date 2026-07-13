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
from api.app.db.models import CocktailDay, CocktailRound, Duel, Player, SoloStats, StarPayment, utcnow
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
    DUEL_DURATION_MINUTES,
    DUEL_MAX_PLAYERS,
    DUEL_REWARD_DISTRIBUTION,
    GAME_KINDS,
    MAX_STAKE_RUB,
    SOLO_MATCH_MAX_ROUNDS,
    SOLO_MATCH_MIN_ROUNDS,
    SOLO_STAKE_PCTS,
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


def _duel_expires_at(duel: Duel) -> datetime:
    """Keep legacy rows readable while every new lobby stores its own deadline."""
    return duel.expires_at or (duel.created_at + timedelta(minutes=DUEL_DURATION_MINUTES))


def _duel_slots(duel: Duel) -> list[tuple[str, int, int | None]]:
    slots: list[tuple[str, int, int | None]] = []
    if duel.creator_joined:
        slots.append(("creator", duel.creator_id, duel.creator_score))
    if duel.opponent_id is not None:
        slots.append(("opponent", duel.opponent_id, duel.opponent_score))
    if duel.third_player_id is not None:
        slots.append(("third", duel.third_player_id, duel.third_score))
    return slots


def _ranked_slots(slots: list[tuple[str, int, int | None]]) -> list[tuple[str, int, int | None]]:
    # Player id is the deterministic tie-breaker. It keeps prize placement stable when
    # two players happen to roll the same score and the result is read again later.
    return sorted(slots, key=lambda item: (item[2] if item[2] is not None else -1, -item[1]), reverse=True)


def _duel_prizes(duel: Duel, slots: list[tuple[str, int, int | None]]) -> dict[int, int]:
    if not slots:
        return {}
    if duel.status == "cancelled" or len(slots) < 2:
        return {player_id: int(duel.stake_rub) for _, player_id, _ in slots}
    ranked = _ranked_slots(slots)
    percentages = DUEL_REWARD_DISTRIBUTION[:len(ranked)]
    if len(ranked) == 2:
        # With two participants the unused third-place share goes to second place.
        percentages = (DUEL_REWARD_DISTRIBUTION[0], 100 - DUEL_REWARD_DISTRIBUTION[0])
    pot = int(duel.stake_rub) * len(ranked)
    prizes = [pot * percent // 100 for percent in percentages]
    prizes[0] += pot - sum(prizes)
    return {ranked[index][1]: prizes[index] for index in range(len(ranked))}


def _duel_payload(session: Session, duel: Duel, viewer_player_id: int | None = None) -> dict:
    creator = session.get(Player, duel.creator_id)
    winner = session.get(Player, duel.winner_id) if duel.winner_id else None
    slots = _duel_slots(duel)
    ranked = _ranked_slots(slots)
    places = {player_id: index + 1 for index, (_, player_id, _) in enumerate(ranked)} if duel.status == "finished" else {}
    prizes = _duel_prizes(duel, slots) if duel.status != "open" else {}
    participants = []
    for _, player_id, score in slots:
        player = session.get(Player, player_id)
        participants.append({
            "player_id": player_id,
            "nickname": player.nickname if player else "—",
            "score": score,
            "place": places.get(player_id),
            "reward_rub": prizes.get(player_id, 0),
        })

    if duel.status == "finished":
        outcome_message = f"Победитель: {winner.nickname}" if winner else "Игра завершена"
    elif duel.status == "cancelled":
        outcome_message = "Недостаточно участников — ставки возвращены"
    else:
        outcome_message = None

    return {
        "id": duel.id,
        "kind": duel.kind,
        "stake_rub": int(duel.stake_rub),
        "creator_nickname": creator.nickname if creator else "—",
        "created_at": duel.created_at.isoformat(),
        "expires_at": _duel_expires_at(duel).isoformat(),
        "status": duel.status,
        "participant_count": len(slots),
        "max_players": DUEL_MAX_PLAYERS,
        "creator_joined": duel.creator_joined,
        "viewer_joined": viewer_player_id in {player_id for _, player_id, _ in slots} if viewer_player_id else False,
        "participants": participants,
        "creator_score": duel.creator_score,
        "opponent_score": duel.opponent_score,
        "third_score": duel.third_score,
        "winner_nickname": winner.nickname if winner else None,
        "outcome_message": outcome_message,
    }


def open_duels(tg_id: int | None = None) -> dict:
    with get_session() as session:
        viewer = get_player(session, tg_id) if tg_id else None
        now = utcnow()
        duels = session.scalars(
            select(Duel).where(Duel.status == "open").order_by(Duel.created_at.desc()).limit(50)
        ).all()
        visible = [duel for duel in duels if _duel_expires_at(duel) > now]
        return {"games": [_duel_payload(session, duel, viewer.id if viewer else None) for duel in visible]}


def create_duel(tg_id: int, body: DuelCreateBody) -> dict:
    stake = _validate_stake(body.stake_rub)
    kind = _validate_kind(body.kind)

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)

        now = utcnow()
        duel = Duel(
            kind=kind,
            stake_rub=stake,
            creator_id=player.id,
            creator_joined=False,
            status="open",
            created_at=now,
            expires_at=now + timedelta(minutes=DUEL_DURATION_MINUTES),
        )
        session.add(duel)
        session.flush()
        # Creating a lobby is free. The stake is charged exactly once, when each player
        # presses Join, including the creator.
        payload = _duel_payload(session, duel, player.id)
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
        joiner = get_player(session, tg_id, for_update=True)
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

        if _duel_expires_at(duel) <= utcnow():
            _resolve_duel_locked(session, duel)
            payload = _duel_payload(session, duel, joiner_id)
            result = {"ok": True, "game": payload, "new_rub": ledger.balance(joiner, "rub")}
            session.commit()
            return result

        slots = _duel_slots(duel)
        if joiner_id in {player_id for _, player_id, _ in slots}:
            raise HTTPException(400, "Ты уже в этой игре")
        if len(slots) >= DUEL_MAX_PLAYERS:
            raise HTTPException(400, "Игра уже заполнена")

        sync_player_income(session, joiner)
        stake = int(duel.stake_rub)
        ledger.spend(session, joiner, "rub", stake, "duel_stake", ref_table="duels", ref_id=duel.id)
        score = _roll_score(session, joiner_id)

        if joiner_id == duel.creator_id:
            duel.creator_joined = True
            duel.creator_score = score
        elif duel.opponent_id is None:
            duel.opponent_id = joiner_id
            duel.opponent_score = score
        else:
            duel.third_player_id = joiner_id
            duel.third_score = score

        session.flush()
        if len(_duel_slots(duel)) >= DUEL_MAX_PLAYERS:
            _resolve_duel_locked(session, duel)

        payload = _duel_payload(session, duel, joiner_id)
        result = {"ok": True, "game": payload, "new_rub": ledger.balance(joiner, "rub")}
        session.commit()
        return result


def _resolve_duel_locked(session: Session, duel: Duel) -> None:
    """Resolve an expired/full lobby. Caller owns the duel row lock."""
    if duel.status != "open":
        return

    slots = _duel_slots(duel)
    players = _lock_players(session, *(player_id for _, player_id, _ in slots))
    if len(slots) < 2:
        for _, player_id, _ in slots:
            player = players.get(player_id)
            if player:
                ledger.grant(session, player, "rub", int(duel.stake_rub), "duel_refund", ref_table="duels", ref_id=duel.id)
        duel.status = "cancelled"
        duel.resolved_at = utcnow()
        return

    ranked = _ranked_slots(slots)
    prizes = _duel_prizes(duel, slots)
    for _, player_id, _ in ranked:
        player = players.get(player_id)
        prize = prizes.get(player_id, 0)
        if player and prize:
            ledger.grant(session, player, "rub", prize, "duel_payout", ref_table="duels", ref_id=duel.id)

    duel.winner_id = ranked[0][1]
    duel.status = "finished"
    duel.resolved_at = utcnow()


def resolve_duel(tg_id: int, duel_id: int) -> dict:
    with get_session() as session:
        viewer = get_player(session, tg_id)
        if not viewer:
            raise HTTPException(404, "Нет игрока")
        duel = session.scalars(select(Duel).where(Duel.id == duel_id).with_for_update()).first()
        if not duel:
            raise HTTPException(404, "Игра не найдена")
        if duel.status == "open":
            if _duel_expires_at(duel) > utcnow():
                raise HTTPException(400, "Время игры еще не закончилось")
            _resolve_duel_locked(session, duel)
        payload = _duel_payload(session, duel, viewer.id)
        session.commit()
        return {"ok": True, "game": payload}


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

        slots = _duel_slots(duel)
        players = _lock_players(session, *(player_id for _, player_id, _ in slots))
        refunded = 0
        for _, participant_id, _ in slots:
            participant = players.get(participant_id)
            if participant:
                ledger.grant(session, participant, "rub", int(duel.stake_rub), "duel_refund", ref_table="duels", ref_id=duel.id)
                if participant_id == player.id:
                    refunded = int(duel.stake_rub)
        duel.status = "cancelled"
        duel.resolved_at = utcnow()

        result = {"ok": True, "refunded_rub": refunded, "new_rub": ledger.balance(player, "rub")}
        session.commit()
        return result


def get_duel(duel_id: int, tg_id: int | None = None) -> dict:
    with get_session() as session:
        duel = session.get(Duel, duel_id)
        if not duel:
            raise HTTPException(404, "Игра не найдена")
        viewer = get_player(session, tg_id) if tg_id else None
        return {"ok": True, "game": _duel_payload(session, duel, viewer.id if viewer else None)}


# ─── Solo games ───────────────────────────────────────────────────────────────


def _solo_roll_bounds(kind: str) -> tuple[int, int]:
    return (1, 5) if kind in {"basketball", "football"} else (1, 6)


def _solo_roll_score(kind: str, roll: int) -> int:
    if kind == "basketball":
        return 2 if roll >= 3 else 0
    if kind == "football":
        return 1 if roll >= 3 else 0
    return roll


def _solo_stake_from_balance(balance_rub: int, stake_pct: int) -> int:
    if stake_pct not in SOLO_STAKE_PCTS:
        raise HTTPException(400, "Недопустимый процент ставки")
    if balance_rub <= 0:
        return 0
    return max(1, int(balance_rub) * stake_pct // 100)


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
    kind = _validate_kind(body.kind)

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)
        stake = _validate_stake(_solo_stake_from_balance(ledger.balance(player, "rub"), body.stake_pct))

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
            "stake_rub": stake,
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


def _cocktail_history(round_: CocktailRound) -> list[dict]:
    try:
        history = json.loads(round_.history or "[]")
    except (TypeError, ValueError):
        return []
    return history if isinstance(history, list) else []


def _get_cocktail_day(session: Session, now: datetime) -> CocktailDay:
    day = now.astimezone(timezone.utc).date()
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


def cocktail_state(tg_id: int) -> dict:
    """Return the current player's persisted cocktail board."""
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")

        now = utcnow()
        day = session.scalars(
            select(CocktailDay).where(CocktailDay.day == now.astimezone(timezone.utc).date())
        ).first()
        round_ = session.get(CocktailRound, player.id)
        current_round = round_ if round_ is not None and round_.expires_at > now else None
        history = _cocktail_history(current_round) if current_round else []
        solved = bool(current_round and current_round.solved_at is not None)
        winner_id = day.winner_player_id if day else None
        return {
            "ok": True,
            "attempts_left": max(0, COCKTAIL_BASE_ATTEMPTS - (current_round.attempts if current_round else 0)),
            "history": history,
            "solved": solved,
            "rewarded": solved and winner_id == player.id,
            "reward_claimed": winner_id is not None,
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

        # The round resets at the next UTC midnight, not 24 hours after it started: a
        # player who solved it a minute in should not wait 23 hours and 59 minutes.
        if round_ is None or round_.expires_at <= now or round_.secret != daily.secret:
            secret = json.loads(daily.secret)
            if round_ is None:
                round_ = CocktailRound(
                    player_id=player.id,
                    secret=daily.secret,
                    history="[]",
                    expires_at=_next_utc_midnight(now),
                )
                session.add(round_)
            else:
                round_.secret = daily.secret
                round_.attempts = 0
                round_.history = "[]"
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
            if daily.winner_player_id is None:
                daily.winner_player_id = player.id
                ledger.grant(session, player, "paw", COCKTAIL_REWARD_PAW, "cocktail_reward")
                result["reward_paw"] = COCKTAIL_REWARD_PAW
                result["new_paw_coins"] = ledger.balance(player, "paw")

        session.commit()
        return result
