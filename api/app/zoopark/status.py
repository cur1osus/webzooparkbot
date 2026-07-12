"""The daily bonus and curing sick animals.

The bonus is a server-generated offer stored in `daily_bonuses`, not a value invented at
claim time. That is what lets the `bonus_rerolls` item property exist: a reroll replaces
the stored offer and spends one of the player's rerolls, and neither the offer nor the
reroll count can be forged by the client.
"""

from __future__ import annotations

from random import SystemRandom

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import Animal, DailyBonus, Locality, Player, utcnow
from api.app.schemas.status import CureBody
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import ledger
from api.app.zoopark.catalog import BONUS_KINDS, BONUS_RANGES, Currency
from api.app.zoopark.income import alive_clause, cure_cost_usd, sync_player_income
from api.app.zoopark.profile import get_player

random = SystemRandom()

_CURRENCY_FIELD: dict[Currency, str] = {"rub": "new_rub", "usd": "new_usd", "paw": "new_paw_coins"}


def _roll_offer() -> tuple[Currency, int]:
    currency = random.choice(BONUS_KINDS)
    low, high = BONUS_RANGES[currency]
    return currency, random.randint(low, high)


def _today_offer(session: Session, player: Player) -> DailyBonus:
    today = utcnow().date()
    offer = session.scalars(
        select(DailyBonus)
        .where(DailyBonus.player_id == player.id, DailyBonus.bonus_date == today)
        .with_for_update()
    ).first()
    if offer is None:
        currency, amount = _roll_offer()
        offer = DailyBonus(player_id=player.id, bonus_date=today, currency=currency, amount=amount)
        session.add(offer)
        session.flush()
    return offer


def _offer_payload(session: Session, player: Player, offer: DailyBonus) -> dict:
    rerolls = bonuses_module.load(session, player.id).total("bonus_rerolls")
    return {
        "currency": offer.currency,
        "amount": offer.amount,
        "claimed": offer.claimed_at is not None,
        "rerolls_left": max(0, rerolls - offer.rerolls_used),
    }


def daily_bonus(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        offer = _today_offer(session, player)
        payload = _offer_payload(session, player, offer)
        session.commit()
        return payload


def reroll_daily_bonus(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        offer = _today_offer(session, player)
        if offer.claimed_at is not None:
            raise HTTPException(400, "Бонус уже получен сегодня")

        allowed = bonuses_module.load(session, player.id).total("bonus_rerolls")
        if offer.rerolls_used >= allowed:
            raise HTTPException(400, "Перебросы закончились")

        offer.currency, offer.amount = _roll_offer()
        offer.rerolls_used += 1

        payload = _offer_payload(session, player, offer)
        session.commit()
        return payload


def claim_bonus(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)

        offer = _today_offer(session, player)
        if offer.claimed_at is not None:
            raise HTTPException(400, "Бонус уже получен сегодня")

        currency: Currency = offer.currency  # type: ignore[assignment]
        new_balance = ledger.grant(
            session, player, currency, offer.amount, "daily_bonus", ref_table="daily_bonuses", ref_id=offer.id
        )
        offer.claimed_at = utcnow()

        result = {
            "ok": True,
            "currency": currency,
            "amount": offer.amount,
            _CURRENCY_FIELD[currency]: new_balance,
        }
        session.commit()
        return result


def cure_animal(tg_id: int, body: CureBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        animal = session.scalars(
            select(Animal)
            .where(Animal.id == body.animal_id, Animal.player_id == player.id, alive_clause())
            .with_for_update()
        ).first()
        if animal is None:
            raise HTTPException(404, "Животное не найдено")
        if animal.sick_since is None:
            raise HTTPException(400, "Животное не болеет")

        # Recompute the price server-side (never trust the client), using the same locality
        # habitat the client saw in the animal payload.
        locality_habitat = None
        if animal.locality_id is not None:
            locality_habitat = session.scalars(
                select(Locality.habitat).where(Locality.id == animal.locality_id)
            ).first()
        bonuses = bonuses_module.load(session, player.id)
        cost_usd = cure_cost_usd(animal, locality_habitat, bonuses)

        ledger.spend(session, player, "usd", cost_usd, "cure_animal", ref_table="animals", ref_id=animal.id)
        animal.sick_since = None
        sync_player_income(session, player, bonuses)

        result = {
            "ok": True,
            "cost_usd": cost_usd,
            "new_usd": ledger.balance(player, "usd"),
            "income_rub_per_min": player.income_rub_per_min,
        }
        session.commit()
        return result
