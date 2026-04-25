from __future__ import annotations

import random

from fastapi import HTTPException

from api.app.db.connection import get_session
from api.app.db.models import SickEvent, User
from api.app.schemas.status import CureBody
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import get_user


def claim_bonus(tg_id: int) -> dict:
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)
        if not user.bonus:
            raise HTTPException(400, "Бонус уже получен сегодня")

        btype = random.choice(["rub", "rub", "usd", "paw_coins"])
        res: dict[str, object] = {"ok": True, "type": btype}

        if btype == "rub":
            amount = random.randint(100, 10000)
            user.rub += amount
            user.bonus = 0
            res.update(amount=amount, new_rub=user.rub, message=f"Получено {amount} ₽")
        elif btype == "usd":
            amount = random.randint(1, 10)
            user.usd += amount
            user.bonus = 0
            res.update(amount=amount, new_usd=user.usd, message=f"Получено ${amount}")
        else:
            amount = random.randint(1, 5)
            user.paw_coins += amount
            user.bonus = 0
            res.update(amount=amount, new_paw_coins=user.paw_coins, message=f"Получено {amount} 🐾")

        session.commit()
        return res


def cure_animal(tg_id: int, body: CureBody) -> dict:
    cost = 10
    try:
        animal_id = int(body.animal_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "Неверный ID животного") from exc
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        uid = user.id
        sick = session.query(SickEvent).filter_by(user_id=uid, animal_id=animal_id).first()
        if not sick:
            raise HTTPException(400, "Животное не болеет")
        if user.paw_coins < cost:
            raise HTTPException(400, f"Нужно {cost} 🐾")
        user.paw_coins -= cost
        session.delete(sick)
        session.commit()
        return {"ok": True, "cost_paw_coins": cost, "new_paw_coins": user.paw_coins}
