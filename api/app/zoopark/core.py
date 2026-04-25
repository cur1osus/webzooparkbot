from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from api.app.core.config import BOT_USERNAME
from api.app.db.connection import get_db
from api.app.db.tables import ZOOPARK_ANIMALS_TABLE, ZOOPARK_AVIARIES_TABLE, ZOOPARK_EXTRA_TABLE, ZOOPARK_USERS_TABLE
from api.app.schemas.core import RegisterBody, SavePayload
from api.app.zoopark.catalog import ANIMAL_BY_ID, ANIMAL_STRING_TO_DB, AVIARY_BY_ID, AVIARY_STRING_TO_DB
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import build_state, get_extra, get_user


def health() -> dict:
    return {"ok": True}


def me(tg_id: int) -> dict:
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


def save(tg_id: int, body: SavePayload) -> dict:
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                return {"ok": False, "rub": 0, "usd": 0, "paw_coins": 0, "balance_seq": 0, "data_version": 0}
            user = dict(user)
            uid = user["id"]
            extra = get_extra(cur, uid)
            user, _income, _expenses = sync_passive_balance(cur, user)
            current_usd = int(user.get("usd", 0))
            current_paw_coins = int(user.get("paw_coins", 0))

            if body.balance_seq >= int(extra.get("balance_seq", 0)):
                current_usd = int(body.usd)
                current_paw_coins = int(body.paw_coins)
                cur.execute(
                    f"UPDATE {ZOOPARK_USERS_TABLE} SET usd=%s, paw_coins=%s WHERE id=%s",
                    (current_usd, current_paw_coins, uid),
                )
                user["usd"] = current_usd
                user["paw_coins"] = current_paw_coins

            if body.data_version >= int(extra.get("data_version", 0)):
                for animal_state in body.animals:
                    db_id = ANIMAL_STRING_TO_DB.get(animal_state.get("animal_id", ""))
                    if not db_id:
                        continue
                    qty = int(animal_state.get("quantity", 0))
                    legacy_animal = ANIMAL_BY_ID[animal_state.get("animal_id")]
                    cur.execute(f"SELECT id FROM {ZOOPARK_ANIMALS_TABLE} WHERE user_id=%s AND animal_info_id=%s", (uid, db_id))
                    if cur.fetchone():
                        cur.execute(f"UPDATE {ZOOPARK_ANIMALS_TABLE} SET quantity=%s WHERE user_id=%s AND animal_info_id=%s", (qty, uid, db_id))
                    elif qty > 0:
                        cur.execute(
                            f"INSERT INTO {ZOOPARK_ANIMALS_TABLE} (user_id, animal_info_id, quantity, income, price) VALUES (%s,%s,%s,%s,%s)",
                            (uid, db_id, qty, legacy_animal["income"], legacy_animal["price"]),
                        )
                for aviary_state in body.aviaries:
                    db_id = AVIARY_STRING_TO_DB.get(aviary_state.get("aviary_id", ""))
                    if not db_id:
                        continue
                    count = int(aviary_state.get("count", 0))
                    legacy_aviary = AVIARY_BY_ID[aviary_state.get("aviary_id")]
                    cur.execute(f"SELECT id FROM {ZOOPARK_AVIARIES_TABLE} WHERE user_id=%s AND aviary_info_id=%s", (uid, db_id))
                    if cur.fetchone():
                        cur.execute(f"UPDATE {ZOOPARK_AVIARIES_TABLE} SET quantity=%s WHERE user_id=%s AND aviary_info_id=%s", (count, uid, db_id))
                    elif count > 0:
                        cur.execute(
                            f"INSERT INTO {ZOOPARK_AVIARIES_TABLE} (user_id, aviary_info_id, price, size, quantity, buy_count) VALUES (%s,%s,%s,%s,%s,%s)",
                            (uid, db_id, legacy_aviary["price"], legacy_aviary["seats"], count, count),
                        )
        db.commit()
        return {
            "ok": True,
            "rub": int(user.get("rub", 0)),
            "usd": current_usd,
            "paw_coins": current_paw_coins,
            "balance_seq": int(user.get("balance_seq", extra.get("balance_seq", 0))),
            "data_version": int(extra.get("data_version", 0)),
        }
    finally:
        db.close()


def register(tg_id: int, body: RegisterBody) -> dict:
    nickname = body.nickname.strip()
    if not (1 <= len(nickname) <= 20):
        raise HTTPException(400, "Никнейм 1-20 символов")
    db = get_db()
    try:
        with db.cursor() as cur:
            if get_user(cur, tg_id):
                raise HTTPException(400, "Уже зарегистрирован")
            cur.execute(f"SELECT id FROM {ZOOPARK_USERS_TABLE} WHERE nickname=%s", (nickname,))
            if cur.fetchone():
                raise HTTPException(400, "Никнейм занят")
            now = datetime.now(timezone.utc)
            cur.execute(
                f"INSERT INTO {ZOOPARK_USERS_TABLE} (id_user, nickname, date_reg, paw_coins, rub, usd, sub_on_chat, sub_on_channel, bonus) "
                "VALUES (%s,%s,%s,0,0,1,0,0,1)",
                (tg_id, nickname, now),
            )
            new_uid = cur.lastrowid
            cur.execute(f"INSERT INTO {ZOOPARK_EXTRA_TABLE} (user_id, balance_seq, data_version) VALUES (%s,0,0)", (new_uid,))
            cur.execute(f"SELECT * FROM {ZOOPARK_USERS_TABLE} WHERE id=%s", (new_uid,))
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


def config() -> dict:
    return {"bot_username": BOT_USERNAME}
