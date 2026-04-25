from __future__ import annotations

import json
import random
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import text

from api.app.core.config import BOT_TOKEN
from api.app.db.connection import get_session
from api.app.db.models import CocktailSession, MpGame, SoloStats, User
from api.app.schemas.games import DonateInvoiceBody, MpCreateBody, SoloStartBody
from api.app.zoopark.catalog import STARS_TO_PAW
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import get_user


COCKTAIL_FRUITS = ["🍓", "🍊", "🍋", "🍇", "🍒", "🍑", "🥝", "🍍"]
MAX_COCKTAIL_ATTEMPTS = 10
SOLO_MATCH_MIN_ROUNDS = 2
SOLO_MATCH_MAX_ROUNDS = 7


def _normalize_bet(value: float) -> int:
    bet_rub = int(value)
    if bet_rub <= 0:
        raise HTTPException(400, "Ставка должна быть больше нуля")
    return bet_rub


def _solo_roll_bounds(game_type: str) -> tuple[int, int]:
    if game_type in {"basketball", "football"}:
        return 1, 5
    return 1, 6


def _solo_roll_score(game_type: str, roll: int) -> int:
    if game_type == "basketball":
        return 2 if roll >= 3 else 0
    if game_type == "football":
        return 1 if roll >= 3 else 0
    return roll


def _simulate_throw_match(game_type: str, *, require_winner: bool) -> tuple[list[dict[str, int]], int, int]:
    history: list[dict[str, int]] = []
    player_score = 0
    opponent_score = 0
    round_no = 1
    roll_min, roll_max = _solo_roll_bounds(game_type)
    target_rounds = random.randint(SOLO_MATCH_MIN_ROUNDS, SOLO_MATCH_MAX_ROUNDS)

    while round_no <= target_rounds or (require_winner and player_score == opponent_score):
        player_roll = random.randint(roll_min, roll_max)
        opponent_roll = random.randint(roll_min, roll_max)
        player_score += _solo_roll_score(game_type, player_roll)
        opponent_score += _solo_roll_score(game_type, opponent_roll)
        history.append({"round": round_no, "player_roll": player_roll, "ai_roll": opponent_roll})
        round_no += 1

    return history, player_score, opponent_score


def api_mpgame_open():
    with get_session() as session:
        rows = session.execute(
            text(
                """
                SELECT g.*, u.nickname AS creator_nickname
                FROM zoopark_mp_games g JOIN zoopark_users u ON u.id=g.creator_id
                WHERE g.status='open' ORDER BY g.created_at DESC LIMIT 20
                """
            )
        ).mappings().all()
        return {
            "games": [
                {
                    "id": row["id"],
                    "game_type": row["game_type"],
                    "bet_rub": int(row["bet_rub"]),
                    "creator_nickname": row["creator_nickname"] or "—",
                    "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
                    "status": row["status"],
                    "winner_nickname": None,
                }
                for row in rows
            ]
        }


def api_mpgame_create(tg_id: int, body: MpCreateBody):
    bet_rub = _normalize_bet(body.bet_rub)
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)
        if user.rub < bet_rub:
            raise HTTPException(400, "Недостаточно рублей")

        game = MpGame(
            game_type=body.game_type, bet_rub=bet_rub,
            creator_id=user.id, status="open",
            created_at=datetime.now(timezone.utc),
        )
        session.add(game)
        user.rub -= bet_rub
        session.flush()
        game_id = game.id
        session.commit()
        return {
            "ok": True,
            "game": {
                "id": game_id,
                "game_type": body.game_type,
                "bet_rub": bet_rub,
                "creator_nickname": user.nickname or "—",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "open",
                "winner_nickname": None,
            },
        }


def api_mpgame_join(tg_id: int, game_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)

        game = session.get(MpGame, game_id)
        if not game:
            raise HTTPException(404, "Игра не найдена")
        if game.status != "open":
            raise HTTPException(400, "Игра недоступна")
        if game.creator_id == user.id:
            raise HTTPException(400, "Нельзя вступить в свою игру")

        bet_rub = game.bet_rub
        if user.rub < bet_rub:
            raise HTTPException(400, "Недостаточно рублей")

        creator_score = random.randint(1, 6)
        opponent_score = random.randint(1, 6)
        while creator_score == opponent_score:
            creator_score = random.randint(1, 6)
            opponent_score = random.randint(1, 6)

        winner_id = game.creator_id if creator_score > opponent_score else user.id
        game.opponent_id = user.id
        game.status = "finished"
        game.creator_score = creator_score
        game.opponent_score = opponent_score
        game.winner_id = winner_id

        user.rub -= bet_rub
        winner = session.get(User, winner_id)
        if winner:
            winner.rub += bet_rub * 2
        creator = session.get(User, game.creator_id)

        session.commit()
        return {
            "ok": True,
            "game": {
                "id": game_id,
                "game_type": game.game_type,
                "bet_rub": int(bet_rub),
                "creator_nickname": creator.nickname if creator else "—",
                "created_at": game.created_at.isoformat() if hasattr(game.created_at, "isoformat") else str(game.created_at),
                "status": "finished",
                "winner_nickname": winner.nickname if winner else "—",
            },
        }


def api_mpgame_throw(game_id: int):
    with get_session() as session:
        row = session.execute(
            text(
                """
                SELECT g.*, u.nickname AS creator_nickname, u2.nickname AS winner_nickname
                FROM zoopark_mp_games g
                JOIN zoopark_users u ON u.id=g.creator_id
                LEFT JOIN zoopark_users u2 ON u2.id=g.winner_id
                WHERE g.id=:gid
                """
            ),
            {"gid": game_id},
        ).mappings().first()
        if not row:
            raise HTTPException(404, "Игра не найдена")
        return {
            "ok": True,
            "game": {
                "id": row["id"],
                "game_type": row["game_type"],
                "bet_rub": int(row["bet_rub"]),
                "creator_nickname": row["creator_nickname"] or "—",
                "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
                "status": row["status"],
                "winner_nickname": row.get("winner_nickname"),
            },
        }


def api_start_solo_game(tg_id: int, body: SoloStartBody):
    bet_rub = _normalize_bet(body.bet_rub)
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)
        if user.rub < bet_rub:
            raise HTTPException(400, "Недостаточно рублей")

        desired_win = random.randint(1, 100) >= 50
        while True:
            history, player_score, ai_score = _simulate_throw_match(body.game_type, require_winner=True)
            if (player_score > ai_score) == desired_win:
                break

        won = desired_win
        is_draw = False
        rub_delta = bet_rub if won else -bet_rub
        new_rub = user.rub + rub_delta
        user.rub = new_rub

        wins_delta = 1 if won else 0
        losses_delta = 1 if not won else 0
        total_won_delta = bet_rub if won else 0
        total_lost_delta = bet_rub if not won else 0

        stats = session.get(SoloStats, user.id)
        if stats:
            stats.games_played += 1
            stats.wins += wins_delta
            stats.losses += losses_delta
            stats.total_won += total_won_delta
            stats.total_lost += total_lost_delta
        else:
            session.add(SoloStats(
                user_id=user.id, games_played=1,
                wins=wins_delta, losses=losses_delta,
                total_won=total_won_delta, total_lost=total_lost_delta,
            ))

        session.commit()
        return {
            "ok": True,
            "result": f"Счёт: {player_score} — {ai_score}",
            "score": player_score,
            "won": won,
            "rub_delta": rub_delta,
            "new_rub": new_rub,
            "history": history,
            "player_score": player_score,
            "ai_score": ai_score,
            "is_draw": is_draw,
        }


def api_get_solo_stats(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            return {"games_played": 0, "wins": 0, "losses": 0, "total_won_rub": 0, "total_lost_rub": 0}
        stats = session.get(SoloStats, user.id)
        if not stats:
            return {"games_played": 0, "wins": 0, "losses": 0, "total_won_rub": 0, "total_lost_rub": 0}
        return {
            "games_played": stats.games_played,
            "wins": stats.wins,
            "losses": stats.losses,
            "total_won_rub": stats.total_won,
            "total_lost_rub": stats.total_lost,
        }


def api_donate_info():
    return {"stars_to_paw": STARS_TO_PAW}


def api_donate_invoice(tg_id: int, body: DonateInvoiceBody):
    if body.stars < 1:
        raise HTTPException(400, "Минимум 1 звезда")
    if not BOT_TOKEN:
        raise HTTPException(503, "Бот не настроен")

    payload = json.dumps({
        "chat_id": tg_id,
        "title": f"Донат {body.stars} ⭐️",
        "description": f"Получи {body.stars * STARS_TO_PAW} 🐾 PawCoins",
        "payload": f"donate_{tg_id}_{body.stars}",
        "currency": "XTR",
        "prices": [{"label": "Stars", "amount": body.stars}],
    }).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read())
    except Exception as exc:
        raise HTTPException(500, f"Ошибка Bot API: {exc}") from exc
    if not data.get("ok"):
        raise HTTPException(500, data.get("description", "Bot API error"))
    return {"invoice_link": data["result"]}


def api_cocktail_guess(tg_id: int, fruits: list[str]):
    if len(fruits) != 4:
        raise HTTPException(400, "Нужно 4 фрукта")

    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")

        cs = session.get(CocktailSession, user.id)
        now = datetime.now(timezone.utc)
        needs_new = (
            not cs
            or cs.won
            or (now - (cs.started_at.replace(tzinfo=timezone.utc) if hasattr(cs.started_at, "replace") else now)) > timedelta(hours=24)
        )
        if needs_new:
            secret = random.sample(COCKTAIL_FRUITS, 4)
            if cs:
                cs.secret = json.dumps(secret)
                cs.attempts = 0
                cs.won = 0
                cs.started_at = now
            else:
                cs = CocktailSession(
                    user_id=user.id, secret=json.dumps(secret),
                    attempts=0, won=0, started_at=now,
                )
                session.add(cs)
            session.flush()

        secret = json.loads(cs.secret)
        cs.attempts += 1
        clues = []
        for index, fruit in enumerate(fruits):
            if fruit == secret[index]:
                clues.append({"pos": index, "status": "correct"})
            elif fruit in secret:
                clues.append({"pos": index, "status": "present"})
            else:
                clues.append({"pos": index, "status": "absent"})

        won = all(clue["status"] == "correct" for clue in clues)
        cs.won = 1 if won else 0
        result: dict[str, object] = {
            "ok": True,
            "won": won,
            "attempts_left": MAX_COCKTAIL_ATTEMPTS - cs.attempts,
            "clues": clues,
        }
        if won:
            reward = 5
            user.paw_coins += reward
            result["reward_paw"] = reward
            result["new_paw_coins"] = user.paw_coins

        session.commit()
        return result
