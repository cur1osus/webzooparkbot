from __future__ import annotations

from fastapi import HTTPException

from api.app.db.connection import get_session
from api.app.db.models import User
from api.app.schemas.economy import BankExchangeBody, BuyAnimalBody, BuyAviaryBody
from api.app.zoopark.catalog import RUB_PER_USD
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import get_user


def buy_animal(tg_id: int, body: BuyAnimalBody) -> dict:
    raise HTTPException(410, "Покупка legacy-животных отключена: животные теперь приходят из паков, разведения и экспедиций")


def buy_aviary(tg_id: int, body: BuyAviaryBody) -> dict:
    raise HTTPException(410, "Вольеры отключены: по GDD размещение происходит через местности")


def bank() -> dict:
    return {
        "rub_rate": RUB_PER_USD,
        "usd_rate": 1 / RUB_PER_USD,
        "rub_discount": 0,
        "usd_discount": 0,
        "min_exchange_rub": RUB_PER_USD,
        "min_exchange_usd": 1,
    }


def bank_exchange(tg_id: int, body: BankExchangeBody) -> dict:
    amount = float(body.amount)
    if amount <= 0:
        raise HTTPException(400, "Сумма должна быть > 0")

    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)

        if body.from_ == "rub":
            cost = int(amount)
            if user.rub < cost:
                raise HTTPException(400, "Недостаточно рублей")
            gain = int(amount / RUB_PER_USD)
            if gain < 1:
                raise HTTPException(400, f"Минимум {RUB_PER_USD} ₽")
            user.rub -= cost
            user.usd += gain
        else:
            cost = int(amount)
            if user.usd < cost:
                raise HTTPException(400, "Недостаточно долларов")
            user.rub += int(amount * RUB_PER_USD)
            user.usd -= cost

        session.commit()
        return {"ok": True, "new_rub": user.rub, "new_usd": user.usd}
