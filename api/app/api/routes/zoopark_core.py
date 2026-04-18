from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import build_state, get_extra, get_user
from api.app.zoopark.runtime import BOT_USERNAME, auth, get_db
from api.app.zoopark.catalog import ANIMAL_BY_ID, ANIMAL_STRING_TO_DB, AVIARY_BY_ID, AVIARY_STRING_TO_DB


router = APIRouter(tags=["zoopark-core"])


class SavePayload(BaseModel):
    rub: float
    usd: float
    paw_coins: float
    animals: list[dict]
    aviaries: list[dict]
    balance_seq: int
    data_version: int


class RegisterBody(BaseModel):
    nickname: str


@router.get("/api/me")
def me(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    tg_id = auth(x_init_data, x_dev_user_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Пользователь не найден")
            user, income, _expenses = sync_passive_balance(cur, user)
            result = build_state(cur, user, income)
        db.commit()
        return result
    finally:
        db.close()


@router.post("/api/save")
def save(
    body: SavePayload,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    tg_id = auth(x_init_data, x_dev_user_id)
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                return {"ok": False}
            uid = user["id"]
            extra = get_extra(cur, uid)
            user, _income, _expenses = sync_passive_balance(cur, user)

            if body.balance_seq >= int(extra.get("balance_seq", 0)):
                cur.execute(
                    "UPDATE users SET usd=%s, paw_coins=%s WHERE id=%s",
                    (int(body.usd), int(body.paw_coins), uid),
                )

            if body.data_version >= int(extra.get("data_version", 0)):
                for animal_state in body.animals:
                    db_id = ANIMAL_STRING_TO_DB.get(animal_state.get("animal_id", ""))
                    if not db_id:
                        continue
                    qty = int(animal_state.get("quantity", 0))
                    legacy_animal = ANIMAL_BY_ID[animal_state.get("animal_id")]
                    cur.execute("SELECT id FROM animals WHERE user_id=%s AND animal_info_id=%s", (uid, db_id))
                    if cur.fetchone():
                        cur.execute("UPDATE animals SET quantity=%s WHERE user_id=%s AND animal_info_id=%s", (qty, uid, db_id))
                    elif qty > 0:
                        cur.execute(
                            "INSERT INTO animals (user_id, animal_info_id, quantity, income, price) VALUES (%s,%s,%s,%s,%s)",
                            (uid, db_id, qty, legacy_animal["income"], legacy_animal["price"]),
                        )
                for aviary_state in body.aviaries:
                    db_id = AVIARY_STRING_TO_DB.get(aviary_state.get("aviary_id", ""))
                    if not db_id:
                        continue
                    count = int(aviary_state.get("count", 0))
                    legacy_aviary = AVIARY_BY_ID[aviary_state.get("aviary_id")]
                    cur.execute("SELECT id FROM aviaries WHERE user_id=%s AND aviary_info_id=%s", (uid, db_id))
                    if cur.fetchone():
                        cur.execute("UPDATE aviaries SET quantity=%s WHERE user_id=%s AND aviary_info_id=%s", (count, uid, db_id))
                    elif count > 0:
                        cur.execute(
                            "INSERT INTO aviaries (user_id, aviary_info_id, price, size, quantity, buy_count) VALUES (%s,%s,%s,%s,%s,%s)",
                            (uid, db_id, legacy_aviary["price"], legacy_aviary["seats"], count, count),
                        )
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/api/register")
def register(
    body: RegisterBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    tg_id = auth(x_init_data, x_dev_user_id)
    nickname = body.nickname.strip()
    if not (1 <= len(nickname) <= 20):
        raise HTTPException(400, "Никнейм 1-20 символов")
    db = get_db()
    try:
        with db.cursor() as cur:
            if get_user(cur, tg_id):
                raise HTTPException(400, "Уже зарегистрирован")
            cur.execute("SELECT id FROM users WHERE nickname=%s", (nickname,))
            if cur.fetchone():
                raise HTTPException(400, "Никнейм занят")
            now = datetime.now(timezone.utc)
            cur.execute(
                "INSERT INTO users (id_user, nickname, date_reg, paw_coins, rub, usd, sub_on_chat, sub_on_channel, bonus) "
                "VALUES (%s,%s,%s,0,0,1,0,0,1)",
                (tg_id, nickname, now),
            )
            new_uid = cur.lastrowid
            cur.execute("INSERT INTO webapp_extra (user_id, balance_seq, data_version) VALUES (%s,0,0)", (new_uid,))
            cur.execute("SELECT * FROM users WHERE id=%s", (new_uid,))
            user = cur.fetchone()
        db.commit()

        db2 = get_db()
        try:
            with db2.cursor() as cur2:
                gs = build_state(cur2, user, 0)
        finally:
            db2.close()
        return {"ok": True, "game_state": gs}
    finally:
        db.close()


@router.get("/api/config")
def config():
    return {"bot_username": BOT_USERNAME}
