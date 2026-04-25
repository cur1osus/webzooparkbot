from __future__ import annotations

import math
import time

from fastapi import HTTPException

from api.app.db.connection import get_session
from api.app.db.models import BankVault, User
from api.app.schemas.economy import BankExchangeBody, BuyAnimalBody, BuyAviaryBody
from api.app.zoopark.catalog import RUB_PER_USD
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import get_user


def _current_rate() -> tuple[int, int]:
    """Return (rub_per_usd, seconds_until_next_update). Rate changes every minute."""
    now = int(time.time())
    minute_seed = now // 60
    # Deterministic pseudo-random ±15% around base rate
    x = math.sin(minute_seed * 127.1 + 311.7) * 43758.5453
    fraction = x - math.floor(x)
    fluctuation = int((fraction - 0.5) * 2 * 0.15 * RUB_PER_USD)
    rate = RUB_PER_USD + fluctuation
    seconds_left = 60 - (now % 60)
    return rate, seconds_left


def _calc_commission(gain: int) -> int:
    """1% commission; min 1$ if gain > 1; 0$ if gain <= 1."""
    if gain <= 1:
        return 0
    commission = int(gain * 0.01)
    return commission if commission > 0 else 1


def _get_vault(session) -> BankVault:
    vault = session.get(BankVault, 1)
    if vault is None:
        vault = BankVault(id=1, usd_balance=0)
        session.add(vault)
        session.flush()
    return vault


def buy_animal(tg_id: int, body: BuyAnimalBody) -> dict:
    raise HTTPException(410, "Покупка legacy-животных отключена: животные теперь приходят из паков, разведения и экспедиций")


def buy_aviary(tg_id: int, body: BuyAviaryBody) -> dict:
    raise HTTPException(410, "Вольеры отключены: по GDD размещение происходит через местности")


def bank() -> dict:
    rate, seconds_left = _current_rate()
    with get_session() as session:
        vault = _get_vault(session)
        vault_usd = vault.usd_balance
    return {
        "rub_rate": rate,
        "usd_rate": 1 / rate,
        "rub_discount": 0,
        "usd_discount": 0,
        "min_exchange_rub": rate,
        "min_exchange_usd": 1,
        "next_update_in": seconds_left,
        "vault_usd": vault_usd,
    }


def bank_exchange(tg_id: int, body: BankExchangeBody) -> dict:
    amount = float(body.amount)
    if amount <= 0:
        raise HTTPException(400, "Сумма должна быть > 0")

    # Transaction 1: sync passive income (short lock, separate from exchange)
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        sync_passive_balance(session, user)
        session.commit()

    # Transaction 2: do the exchange (short lock)
    with get_session() as session:
        user = get_user(session, tg_id)
        rate, _ = _current_rate()
        vault = _get_vault(session)
        if body.from_ == "rub":
            cost = int(amount)
            if user.rub < cost:
                raise HTTPException(400, "Недостаточно рублей")
            gain = int(amount / rate)
            if gain < 1:
                raise HTTPException(400, f"Минимум {rate} ₽")
            commission = _calc_commission(gain)
            user.rub -= cost
            user.usd += gain - commission
            vault.usd_balance += commission
        else:
            cost = int(amount)
            if user.usd < cost:
                raise HTTPException(400, "Недостаточно долларов")
            user.rub += int(amount * rate)
            user.usd -= cost

        session.commit()
        return {"ok": True, "new_rub": user.rub, "new_usd": user.usd}
