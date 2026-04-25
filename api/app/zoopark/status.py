from __future__ import annotations

import random

from fastapi import HTTPException

from api.app.db.connection import get_db
from api.app.db.tables import ZOOPARK_SICK_EVENTS_TABLE, ZOOPARK_USERS_TABLE
from api.app.schemas.status import CureBody
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import get_user


def claim_bonus(tg_id: int) -> dict:
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)
            if not user["bonus"]:
                raise HTTPException(400, "Бонус уже получен сегодня")

            uid = user["id"]
            rub = int(user["rub"])
            usd = int(user["usd"])
            paw = int(user["paw_coins"])
            btype = random.choice(["rub", "rub", "usd", "paw_coins"])
            res: dict[str, object] = {"ok": True, "type": btype}

            if btype == "rub":
                amount = random.randint(100, 10000)
                cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s, bonus=0 WHERE id=%s", (rub + amount, uid))
                res.update(amount=amount, new_rub=rub + amount, message=f"Получено {amount} ₽")
            elif btype == "usd":
                amount = random.randint(1, 10)
                cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET usd=%s, bonus=0 WHERE id=%s", (usd + amount, uid))
                res.update(amount=amount, new_usd=usd + amount, message=f"Получено ${amount}")
            else:
                amount = random.randint(1, 5)
                cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET paw_coins=%s, bonus=0 WHERE id=%s", (paw + amount, uid))
                res.update(amount=amount, new_paw_coins=paw + amount, message=f"Получено {amount} 🐾")
        db.commit()
        return res
    finally:
        db.close()


def cure_animal(tg_id: int, body: CureBody) -> dict:
    cost = 10
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            uid = user["id"]
            cur.execute(f"SELECT id FROM {ZOOPARK_SICK_EVENTS_TABLE} WHERE user_id=%s AND animal_id=%s", (uid, body.animal_id))
            if not cur.fetchone():
                raise HTTPException(400, "Животное не болеет")
            paw = int(user["paw_coins"])
            if paw < cost:
                raise HTTPException(400, f"Нужно {cost} 🐾")
            new_paw = paw - cost
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET paw_coins=%s WHERE id=%s", (new_paw, uid))
            cur.execute(f"DELETE FROM {ZOOPARK_SICK_EVENTS_TABLE} WHERE user_id=%s AND animal_id=%s", (uid, body.animal_id))
        db.commit()
        return {"ok": True, "cost_paw_coins": cost, "new_paw_coins": new_paw}
    finally:
        db.close()
