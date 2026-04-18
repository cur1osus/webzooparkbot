from __future__ import annotations

import random

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import get_user
from api.app.zoopark.runtime import auth, get_db


router = APIRouter(tags=["zoopark-status"])


class CureBody(BaseModel):
    animal_id: str


@router.post("/api/claim_bonus")
def claim_bonus(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    tg_id = auth(x_init_data, x_dev_user_id)
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
                cur.execute("UPDATE users SET rub=%s, bonus=0 WHERE id=%s", (rub + amount, uid))
                res.update(amount=amount, new_rub=rub + amount, message=f"Получено {amount} ₽")
            elif btype == "usd":
                amount = random.randint(1, 10)
                cur.execute("UPDATE users SET usd=%s, bonus=0 WHERE id=%s", (usd + amount, uid))
                res.update(amount=amount, new_usd=usd + amount, message=f"Получено ${amount}")
            else:
                amount = random.randint(1, 5)
                cur.execute("UPDATE users SET paw_coins=%s, bonus=0 WHERE id=%s", (paw + amount, uid))
                res.update(amount=amount, new_paw_coins=paw + amount, message=f"Получено {amount} 🐾")
        db.commit()
        return res
    finally:
        db.close()


@router.post("/api/cure_animal")
def cure_animal(
    body: CureBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    tg_id = auth(x_init_data, x_dev_user_id)
    cost = 10
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            uid = user["id"]
            cur.execute("SELECT id FROM sick_events WHERE user_id=%s AND animal_id=%s", (uid, body.animal_id))
            if not cur.fetchone():
                raise HTTPException(400, "Животное не болеет")
            paw = int(user["paw_coins"])
            if paw < cost:
                raise HTTPException(400, f"Нужно {cost} 🐾")
            new_paw = paw - cost
            cur.execute("UPDATE users SET paw_coins=%s WHERE id=%s", (new_paw, uid))
            cur.execute("DELETE FROM sick_events WHERE user_id=%s AND animal_id=%s", (uid, body.animal_id))
        db.commit()
        return {"ok": True, "cost_paw_coins": cost, "new_paw_coins": new_paw}
    finally:
        db.close()
