"""The bank.

A one-way funnel: rubles come out of the zoo, dollars go into the forge. There is no
usd → rub direction, exactly as in the Telegram bot, and that single fact is what makes
a visibly swinging rate safe. The previous implementation quoted both directions around
a ±15% oscillation with a 2% spread, so a player who waited for a cheap minute to buy and
a dear one to sell earned 26% per round trip, risk-free and without limit.

The rate is a random walk persisted one row per minute in `bank_rates`, clamped to
[RATE_MIN, RATE_MAX]. It used to be `HMAC(secret, current_minute)` — deterministic, and
therefore needing a server secret to stop players precomputing tomorrow's quotes. State
needs no secret, and it gives the client a real 24-hour chart.
"""

from __future__ import annotations

import time
from random import SystemRandom

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import BankRate, Player
from api.app.schemas.economy import BankExchangeBody
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import ledger
from api.app.zoopark.bonuses import Bonuses
from api.app.zoopark.catalog import (
    BANK_FEE_PERCENT,
    RATE_MAX_RUB_PER_USD,
    RATE_MIN_RUB_PER_USD,
    RATE_PERIOD_SECONDS,
    RATE_START_RUB_PER_USD,
    RATE_STEPS,
    REFERRAL_PERCENT,
)
from api.app.zoopark.income import sync_player_income
from api.app.zoopark.profile import get_player

random = SystemRandom()


def current_period(now: int | None = None) -> int:
    return (int(time.time()) if now is None else now) // RATE_PERIOD_SECONDS


def _clamp(rate: int) -> int:
    return max(RATE_MIN_RUB_PER_USD, min(RATE_MAX_RUB_PER_USD, rate))


def _next_rate(previous: int) -> int:
    step = random.choice(RATE_STEPS) * random.choice((1, -1))
    return _clamp(previous + step)


def base_rate(session: Session, now: int | None = None) -> int:
    """The published rub-per-usd rate for the current minute, minting it if needed."""
    period = current_period(now)
    existing = session.get(BankRate, period)
    if existing is not None:
        return int(existing.rate_rub_per_usd)

    previous = session.scalars(
        select(BankRate).order_by(BankRate.period.desc()).limit(1)
    ).first()
    rate = _next_rate(int(previous.rate_rub_per_usd)) if previous else RATE_START_RUB_PER_USD

    # The primary key on `period` settles the race: whoever loses reads the winner's row.
    try:
        with session.begin_nested():
            session.add(BankRate(period=period, rate_rub_per_usd=rate))
    except IntegrityError:
        pass

    row = session.get(BankRate, period)
    return int(row.rate_rub_per_usd) if row else rate


def effective_rate(session: Session, player_id: int, bonuses: Bonuses | None = None, now: int | None = None) -> tuple[int, int]:
    """(rate the player pays, published rate). The `discount_bank` item property makes
    dollars cheaper for its owner; it can never make them free (the cap is 80%)."""
    published = base_rate(session, now)
    active = bonuses if bonuses is not None else bonuses_module.load(session, player_id)
    discounted = max(1, int(published * active.bank_rate_multiplier()))
    return discounted, published


def seconds_until_next_rate(now: int | None = None) -> int:
    moment = int(time.time()) if now is None else now
    return RATE_PERIOD_SECONDS - (moment % RATE_PERIOD_SECONDS)


def _bank_fee(gross_usd: int) -> int:
    """`BANK_FEE_PERCENT` of the dollars bought, at least 1 once more than one is bought.

    A sub-dollar purchase is free, which is harmless here: with no way to sell dollars
    back, a free small trade cannot be a round trip.
    """
    if gross_usd <= 1:
        return 0
    fee = int(gross_usd * BANK_FEE_PERCENT / 100)
    return max(fee, 1)


def rate_history(session: Session, points: int = 60) -> list[dict]:
    rows = session.scalars(
        select(BankRate).order_by(BankRate.period.desc()).limit(points)
    ).all()
    return [
        {"period": int(row.period), "rate": int(row.rate_rub_per_usd)}
        for row in reversed(list(rows))
    ]


def bank(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        rate, published = effective_rate(session, player.id)
        history = rate_history(session)
        session.commit()
        return {
            "rate_rub_per_usd": rate,
            "base_rate_rub_per_usd": published,
            "fee_percent": BANK_FEE_PERCENT,
            "referral_percent": REFERRAL_PERCENT if player.referred_by_id else 0,
            "min_exchange_rub": rate,
            "next_update_in": seconds_until_next_rate(),
            "treasury_usd": ledger.treasury_balance(session, "usd"),
            "history": history,
        }


def exchange(tg_id: int, body: BankExchangeBody) -> dict:
    """Buy dollars with rubles. The only conversion the game has."""
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)

        rate, _published = effective_rate(session, player.id)
        budget = ledger.balance(player, "rub") if body.exchange_all else body.amount_rub
        if budget <= 0:
            raise HTTPException(400, "Сумма должна быть больше нуля")
        if budget > ledger.balance(player, "rub"):
            raise HTTPException(400, "Недостаточно рублей")

        gross_usd = budget // rate
        if gross_usd < 1:
            raise HTTPException(400, f"Недостаточно рублей для обмена (нужно ≥ {rate} ₽)")

        # Only the rubles that actually became dollars are charged; the remainder stays.
        spent_rub = gross_usd * rate
        fee_usd = _bank_fee(gross_usd)
        net_usd = gross_usd - fee_usd

        referrer_usd = 0
        referrer = None
        if player.referred_by_id:
            referrer_usd = int(net_usd * REFERRAL_PERCENT / 100)
            if referrer_usd > 0:
                referrer = session.get(Player, player.referred_by_id, with_for_update=True)
                if referrer is None:
                    referrer_usd = 0

        ledger.spend(session, player, "rub", spent_rub, "bank_buy_usd")
        ledger.grant(session, player, "usd", net_usd - referrer_usd, "bank_buy_usd")
        ledger.credit_treasury(session, "usd", fee_usd, "bank_fee", ref_table="players", ref_id=player.id)
        if referrer is not None and referrer_usd > 0:
            ledger.grant(session, referrer, "usd", referrer_usd, "referral_exchange", ref_table="players", ref_id=player.id)

        result = {
            "ok": True,
            "spent_rub": spent_rub,
            "received_usd": net_usd - referrer_usd,
            "fee_usd": fee_usd,
            "referrer_usd": referrer_usd,
            "rate_rub_per_usd": rate,
            "new_rub": ledger.balance(player, "rub"),
            "new_usd": ledger.balance(player, "usd"),
        }
        session.commit()
        return result
