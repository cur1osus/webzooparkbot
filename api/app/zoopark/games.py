from __future__ import annotations

import json
import random
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import BaseModel

from api.app.zoopark.catalog import STARS_TO_PAW
from api.app.zoopark.db_tables import (
    ZOOPARK_COCKTAIL_SESSIONS_TABLE,
    ZOOPARK_MP_GAMES_TABLE,
    ZOOPARK_SOLO_STATS_TABLE,
    ZOOPARK_USERS_TABLE,
)
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import get_user
from api.app.zoopark.runtime import BOT_TOKEN, get_db


COCKTAIL_FRUITS = ["🍓", "🍊", "🍋", "🍇", "🍒", "🍑", "🥝", "🍍"]
MAX_COCKTAIL_ATTEMPTS = 10
BASKETBALL_ROUNDS = 5


class DonateInvoiceBody(BaseModel):
    stars: int


class MpCreateBody(BaseModel):
    game_type: str
    bet_rub: float


class SoloStartBody(BaseModel):
    game_type: str
    bet_rub: float


def _basketball_roll_score(roll: int) -> int:
    return 2 if roll >= 3 else 0


def _simulate_basketball_match(*, require_winner: bool) -> tuple[list[dict[str, int]], int, int]:
    history: list[dict[str, int]] = []
    player_score = 0
    opponent_score = 0
    round_no = 1

    while round_no <= BASKETBALL_ROUNDS or (require_winner and player_score == opponent_score):
        player_roll = random.randint(0, 5)
        opponent_roll = random.randint(0, 5)
        player_score += _basketball_roll_score(player_roll)
        opponent_score += _basketball_roll_score(opponent_roll)
        history.append({"round": round_no, "player_roll": player_roll, "ai_roll": opponent_roll})
        round_no += 1

    return history, player_score, opponent_score


def api_mpgame_open():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                f"""
                SELECT g.*, u.nickname AS creator_nickname
                FROM {ZOOPARK_MP_GAMES_TABLE} g JOIN {ZOOPARK_USERS_TABLE} u ON u.id=g.creator_id
                WHERE g.status='open' ORDER BY g.created_at DESC LIMIT 20
                """
            )
            rows = cur.fetchall()
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
    finally:
        db.close()


def api_mpgame_create(
    tg_id: int,
    body: MpCreateBody,
):
    bet_rub = int(body.bet_rub)
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)
            if int(user["rub"]) < bet_rub:
                raise HTTPException(400, "Недостаточно рублей")

            cur.execute(
                f"INSERT INTO {ZOOPARK_MP_GAMES_TABLE} (game_type, bet_rub, creator_id) VALUES (%s,%s,%s)",
                (body.game_type, bet_rub, user["id"]),
            )
            game_id = cur.lastrowid
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=rub-%s WHERE id=%s", (bet_rub, user["id"]))
        db.commit()
        return {
            "ok": True,
            "game": {
                "id": game_id,
                "game_type": body.game_type,
                "bet_rub": bet_rub,
                "creator_nickname": user["nickname"] or "—",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "open",
                "winner_nickname": None,
            },
        }
    finally:
        db.close()


def api_mpgame_join(
    tg_id: int,
    game_id: int,
):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)

            cur.execute(f"SELECT * FROM {ZOOPARK_MP_GAMES_TABLE} WHERE id=%s", (game_id,))
            game = cur.fetchone()
            if not game:
                raise HTTPException(404, "Игра не найдена")
            if game["status"] != "open":
                raise HTTPException(400, "Игра недоступна")
            if game["creator_id"] == user["id"]:
                raise HTTPException(400, "Нельзя вступить в свою игру")

            bet_rub = int(game["bet_rub"])
            if int(user["rub"]) < bet_rub:
                raise HTTPException(400, "Недостаточно рублей")

            if game["game_type"] == "basketball":
                _history, creator_score, opponent_score = _simulate_basketball_match(require_winner=True)
            else:
                creator_score = random.randint(1, 6)
                opponent_score = random.randint(1, 6)
                while creator_score == opponent_score:
                    creator_score = random.randint(1, 6)
                    opponent_score = random.randint(1, 6)

            winner_id = game["creator_id"] if creator_score > opponent_score else user["id"]
            cur.execute(
                f"UPDATE {ZOOPARK_MP_GAMES_TABLE} SET opponent_id=%s, status='finished', creator_score=%s, opponent_score=%s, winner_id=%s WHERE id=%s",
                (user["id"], creator_score, opponent_score, winner_id, game_id),
            )
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=rub-%s WHERE id=%s", (bet_rub, user["id"]))
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=rub+%s WHERE id=%s", (bet_rub * 2, winner_id))
            cur.execute(f"SELECT nickname FROM {ZOOPARK_USERS_TABLE} WHERE id=%s", (winner_id,))
            winner = cur.fetchone()
            cur.execute(f"SELECT nickname FROM {ZOOPARK_USERS_TABLE} WHERE id=%s", (game["creator_id"],))
            creator = cur.fetchone()
        db.commit()
        return {
            "ok": True,
            "game": {
                "id": game_id,
                "game_type": game["game_type"],
                "bet_rub": bet_rub,
                "creator_nickname": creator["nickname"] if creator else "—",
                "created_at": game["created_at"].isoformat() if hasattr(game["created_at"], "isoformat") else str(game["created_at"]),
                "status": "finished",
                "winner_nickname": winner["nickname"] if winner else "—",
            },
        }
    finally:
        db.close()


def api_mpgame_throw(
    game_id: int,
):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                f"""
                SELECT g.*, u.nickname AS creator_nickname, u2.nickname AS winner_nickname
                FROM {ZOOPARK_MP_GAMES_TABLE} g
                JOIN {ZOOPARK_USERS_TABLE} u ON u.id=g.creator_id
                LEFT JOIN {ZOOPARK_USERS_TABLE} u2 ON u2.id=g.winner_id
                WHERE g.id=%s
                """,
                (game_id,),
            )
            game = cur.fetchone()
            if not game:
                raise HTTPException(404, "Игра не найдена")
        return {
            "ok": True,
            "game": {
                "id": game["id"],
                "game_type": game["game_type"],
                "bet_rub": int(game["bet_rub"]),
                "creator_nickname": game["creator_nickname"] or "—",
                "created_at": game["created_at"].isoformat() if hasattr(game["created_at"], "isoformat") else str(game["created_at"]),
                "status": game["status"],
                "winner_nickname": game.get("winner_nickname"),
            },
        }
    finally:
        db.close()


def api_start_solo_game(
    tg_id: int,
    body: SoloStartBody,
):
    bet_rub = int(body.bet_rub)
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)
            if int(user["rub"]) < bet_rub:
                raise HTTPException(400, "Недостаточно рублей")

            history: list[dict[str, int]] | None = None
            player_score: int | None = None
            ai_score: int | None = None
            is_draw = False

            if body.game_type == "basketball":
                history, player_score, ai_score = _simulate_basketball_match(require_winner=False)
                is_draw = player_score == ai_score
                score = player_score
                won = player_score > ai_score
                rub_delta = bet_rub if won else 0 if is_draw else -bet_rub
                result_text = f"Счёт: {player_score} — {ai_score}"
            else:
                score = random.randint(1, 100)
                won = score >= 50
                rub_delta = bet_rub if won else -bet_rub
                result_text = f"Счёт: {score}"

            new_rub = int(user["rub"]) + rub_delta
            wins_delta = 1 if won else 0
            losses_delta = 1 if not won and not is_draw else 0
            total_won_delta = bet_rub if won else 0
            total_lost_delta = bet_rub if not won and not is_draw else 0

            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (new_rub, user["id"]))
            cur.execute(
                f"INSERT INTO {ZOOPARK_SOLO_STATS_TABLE} (user_id, games_played, wins, losses, total_won, total_lost) "
                "VALUES (%s,1,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE "
                "games_played=games_played+1, wins=wins+%s, losses=losses+%s, "
                "total_won=total_won+%s, total_lost=total_lost+%s",
                (
                    user["id"],
                    wins_delta,
                    losses_delta,
                    total_won_delta,
                    total_lost_delta,
                    wins_delta,
                    losses_delta,
                    total_won_delta,
                    total_lost_delta,
                ),
            )
        db.commit()
        response = {
            "ok": True,
            "result": result_text,
            "score": score,
            "won": won,
            "rub_delta": rub_delta,
            "new_rub": new_rub,
        }

        if history is not None:
            response["history"] = history
            response["player_score"] = player_score
            response["ai_score"] = ai_score
            response["is_draw"] = is_draw

        return response
    finally:
        db.close()


def api_get_solo_stats(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                return {"games_played": 0, "wins": 0, "losses": 0, "total_won_rub": 0, "total_lost_rub": 0}
            cur.execute(f"SELECT * FROM {ZOOPARK_SOLO_STATS_TABLE} WHERE user_id=%s", (user["id"],))
            row = cur.fetchone()

        if not row:
            return {"games_played": 0, "wins": 0, "losses": 0, "total_won_rub": 0, "total_lost_rub": 0}

        return {
            "games_played": int(row["games_played"]),
            "wins": int(row["wins"]),
            "losses": int(row["losses"]),
            "total_won_rub": int(row["total_won"]),
            "total_lost_rub": int(row["total_lost"]),
        }
    finally:
        db.close()


def api_donate_info():
    return {"stars_to_paw": STARS_TO_PAW}


def api_donate_invoice(
    tg_id: int,
    body: DonateInvoiceBody,
):
    if body.stars < 1:
        raise HTTPException(400, "Минимум 1 звезда")
    if not BOT_TOKEN:
        raise HTTPException(503, "Бот не настроен")

    payload = json.dumps(
        {
            "chat_id": tg_id,
            "title": f"Донат {body.stars} ⭐️",
            "description": f"Получи {body.stars * STARS_TO_PAW} 🐾 PawCoins",
            "payload": f"donate_{tg_id}_{body.stars}",
            "currency": "XTR",
            "prices": [{"label": "Stars", "amount": body.stars}],
        }
    ).encode()
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

    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            cur.execute(f"SELECT * FROM {ZOOPARK_COCKTAIL_SESSIONS_TABLE} WHERE user_id=%s", (user["id"],))
            session = cur.fetchone()
            now = datetime.now(timezone.utc)
            needs_new = (
                not session
                or session["won"]
                or (now - (session["started_at"].replace(tzinfo=timezone.utc) if hasattr(session["started_at"], "replace") else now)) > timedelta(hours=24)
            )
            if needs_new:
                secret = random.sample(COCKTAIL_FRUITS, 4)
                cur.execute(
                    f"INSERT INTO {ZOOPARK_COCKTAIL_SESSIONS_TABLE} (user_id, secret, attempts, won, started_at) VALUES (%s,%s,0,0,NOW()) "
                    "ON DUPLICATE KEY UPDATE secret=%s, attempts=0, won=0, started_at=NOW()",
                    (user["id"], json.dumps(secret), json.dumps(secret)),
                )
                db.commit()
                cur.execute(f"SELECT * FROM {ZOOPARK_COCKTAIL_SESSIONS_TABLE} WHERE user_id=%s", (user["id"],))
                session = cur.fetchone()

            secret = json.loads(session["secret"])
            attempts = int(session["attempts"]) + 1
            clues = []
            for index, fruit in enumerate(fruits):
                if fruit == secret[index]:
                    clues.append({"pos": index, "status": "correct"})
                elif fruit in secret:
                    clues.append({"pos": index, "status": "present"})
                else:
                    clues.append({"pos": index, "status": "absent"})

            won = all(clue["status"] == "correct" for clue in clues)
            cur.execute(f"UPDATE {ZOOPARK_COCKTAIL_SESSIONS_TABLE} SET attempts=%s, won=%s WHERE user_id=%s", (attempts, 1 if won else 0, user["id"]))
            result: dict[str, object] = {
                "ok": True,
                "won": won,
                "attempts_left": MAX_COCKTAIL_ATTEMPTS - attempts,
                "clues": clues,
            }
            if won:
                reward = 5
                cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET paw_coins=paw_coins+%s WHERE id=%s", (reward, user["id"]))
                cur.execute(f"SELECT paw_coins FROM {ZOOPARK_USERS_TABLE} WHERE id=%s", (user["id"],))
                paw_row = cur.fetchone()
                result["reward_paw"] = reward
                result["new_paw_coins"] = int(paw_row["paw_coins"])
        db.commit()
        return result
    finally:
        db.close()
