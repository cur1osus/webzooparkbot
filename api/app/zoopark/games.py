from __future__ import annotations

import json
import random
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import BaseModel

from api.app.zoopark.catalog import STARS_TO_PAW
from api.app.zoopark.profile import get_user
from api.app.zoopark.runtime import BOT_TOKEN, get_db


COCKTAIL_FRUITS = ["🍓", "🍊", "🍋", "🍇", "🍒", "🍑", "🥝", "🍍"]
MAX_COCKTAIL_ATTEMPTS = 10


class DonateInvoiceBody(BaseModel):
    stars: int


class MpCreateBody(BaseModel):
    game_type: str
    bet_rub: float


class SoloStartBody(BaseModel):
    game_type: str
    bet_rub: float


def api_mpgame_open():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT g.*, u.nickname AS creator_nickname
                FROM mp_games_new g JOIN users u ON u.id=g.creator_id
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
            if int(user["rub"]) < bet_rub:
                raise HTTPException(400, "Недостаточно рублей")

            cur.execute(
                "INSERT INTO mp_games_new (game_type, bet_rub, creator_id) VALUES (%s,%s,%s)",
                (body.game_type, bet_rub, user["id"]),
            )
            game_id = cur.lastrowid
            cur.execute("UPDATE users SET rub=rub-%s WHERE id=%s", (bet_rub, user["id"]))
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

            cur.execute("SELECT * FROM mp_games_new WHERE id=%s", (game_id,))
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

            creator_score = random.randint(1, 6)
            opponent_score = random.randint(1, 6)
            while creator_score == opponent_score:
                creator_score = random.randint(1, 6)
                opponent_score = random.randint(1, 6)

            winner_id = game["creator_id"] if creator_score > opponent_score else user["id"]
            cur.execute(
                "UPDATE mp_games_new SET opponent_id=%s, status='finished', creator_score=%s, opponent_score=%s, winner_id=%s WHERE id=%s",
                (user["id"], creator_score, opponent_score, winner_id, game_id),
            )
            cur.execute("UPDATE users SET rub=rub-%s WHERE id=%s", (bet_rub, user["id"]))
            cur.execute("UPDATE users SET rub=rub+%s WHERE id=%s", (bet_rub * 2, winner_id))
            cur.execute("SELECT nickname FROM users WHERE id=%s", (winner_id,))
            winner = cur.fetchone()
            cur.execute("SELECT nickname FROM users WHERE id=%s", (game["creator_id"],))
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
                """
                SELECT g.*, u.nickname AS creator_nickname, u2.nickname AS winner_nickname
                FROM mp_games_new g
                JOIN users u ON u.id=g.creator_id
                LEFT JOIN users u2 ON u2.id=g.winner_id
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
            if int(user["rub"]) < bet_rub:
                raise HTTPException(400, "Недостаточно рублей")

            score = random.randint(1, 100)
            won = score >= 50
            rub_delta = bet_rub if won else -bet_rub
            new_rub = int(user["rub"]) + rub_delta
            cur.execute("UPDATE users SET rub=%s WHERE id=%s", (new_rub, user["id"]))
            cur.execute(
                "INSERT INTO solo_stats (user_id, games_played, wins, losses, total_won, total_lost) "
                "VALUES (%s,1,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE "
                "games_played=games_played+1, wins=wins+%s, losses=losses+%s, "
                "total_won=total_won+%s, total_lost=total_lost+%s",
                (
                    user["id"],
                    1 if won else 0,
                    0 if won else 1,
                    bet_rub if won else 0,
                    0 if won else bet_rub,
                    1 if won else 0,
                    0 if won else 1,
                    bet_rub if won else 0,
                    0 if won else bet_rub,
                ),
            )
        db.commit()
        return {
            "ok": True,
            "result": f"Счёт: {score}",
            "score": score,
            "won": won,
            "rub_delta": rub_delta,
            "new_rub": new_rub,
        }
    finally:
        db.close()


def api_get_solo_stats(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                return {"games_played": 0, "wins": 0, "losses": 0, "total_won_rub": 0, "total_lost_rub": 0}
            cur.execute("SELECT * FROM solo_stats WHERE user_id=%s", (user["id"],))
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

            cur.execute("SELECT * FROM cocktail_sessions WHERE user_id=%s", (user["id"],))
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
                    "INSERT INTO cocktail_sessions (user_id, secret, attempts, won, started_at) VALUES (%s,%s,0,0,NOW()) "
                    "ON DUPLICATE KEY UPDATE secret=%s, attempts=0, won=0, started_at=NOW()",
                    (user["id"], json.dumps(secret), json.dumps(secret)),
                )
                db.commit()
                cur.execute("SELECT * FROM cocktail_sessions WHERE user_id=%s", (user["id"],))
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
            cur.execute("UPDATE cocktail_sessions SET attempts=%s, won=%s WHERE user_id=%s", (attempts, 1 if won else 0, user["id"]))
            result: dict[str, object] = {
                "ok": True,
                "won": won,
                "attempts_left": MAX_COCKTAIL_ATTEMPTS - attempts,
                "clues": clues,
            }
            if won:
                reward = 5
                cur.execute("UPDATE users SET paw_coins=paw_coins+%s WHERE id=%s", (reward, user["id"]))
                cur.execute("SELECT paw_coins FROM users WHERE id=%s", (user["id"],))
                paw_row = cur.fetchone()
                result["reward_paw"] = reward
                result["new_paw_coins"] = int(paw_row["paw_coins"])
        db.commit()
        return result
    finally:
        db.close()
