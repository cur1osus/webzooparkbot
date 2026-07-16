"""The daily bonus and curing sick animals.

The bonus is a server-generated offer stored in `daily_bonuses`, not a value invented at
claim time. That is what lets the `bonus_rerolls` item property exist: a reroll replaces
the stored offer and spends one of the player's rerolls, and neither the offer nor the
reroll count can be forged by the client.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import Animal, DailyBonus, Locality, Player, utcnow
from api.app.schemas.status import CureBody
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import ledger
from api.app.zoopark.catalog import HABITATS, SPECIES_BY_CODE, SPECIES_ID_BY_CODE, Currency
from api.app.zoopark.daily_bonus import roll_daily_bonus_offer
from api.app.zoopark.income import alive_clause, cure_cost_usd, sync_player_income
from api.app.zoopark.profile import get_player
from api.app.zoopark.progression import create_animal, roll_genes, roll_habitat
from api.app.zoopark.season import ensure_player_season

_CURRENCY_FIELD: dict[Currency, str] = {"rub": "new_rub", "usd": "new_usd", "paw": "new_paw_coins"}
_HABITAT_REWARD_META = {
    "desert": ("Пустыня", "🏜️"),
    "mountains": ("Горы", "⛰️"),
    "forest": ("Лес", "🌲"),
    "fields": ("Поля", "🌾"),
    "antarctica": ("Антарктида", "🏔️"),
}


def _today_offer(session: Session, player: Player) -> DailyBonus:
    today = utcnow().date()
    offer = session.scalars(
        select(DailyBonus)
        .where(DailyBonus.player_id == player.id, DailyBonus.bonus_date == today)
        .with_for_update()
    ).first()
    if offer is None:
        currency, amount, reward_code = roll_daily_bonus_offer(session, player)
        offer = DailyBonus(
            player_id=player.id,
            bonus_date=today,
            currency=currency,
            amount=amount,
            reward_code=reward_code,
        )
        session.add(offer)
        session.flush()
    return offer


def _offer_payload(session: Session, player: Player, offer: DailyBonus) -> dict:
    rerolls = bonuses_module.load(session, player.id).total("bonus_rerolls")
    payload = {
        "currency": offer.currency,
        "amount": offer.amount,
        "reward_code": offer.reward_code,
        "claimed": offer.claimed_at is not None,
        "rerolls_left": max(0, rerolls - offer.rerolls_used),
    }
    if offer.currency == "animal" and offer.reward_code in SPECIES_BY_CODE:
        species = SPECIES_BY_CODE[offer.reward_code]
        payload.update(reward_name=species["name"], reward_emoji=species["emoji"])
    elif offer.currency == "locality" and offer.reward_code in HABITATS:
        name, emoji = _HABITAT_REWARD_META[offer.reward_code]
        payload.update(reward_name=name, reward_emoji=emoji)
    return payload


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

        offer.currency, offer.amount, offer.reward_code = roll_daily_bonus_offer(session, player)
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

        new_balance = None
        balance_field = None
        reward_name = None
        reward_emoji = None
        if offer.currency in ("rub", "usd", "paw"):
            currency: Currency = offer.currency  # type: ignore[assignment]
            # Resolved here, off the same narrowing that produced the balance: `currency`
            # widens back to `str` outside this branch, and the column is *not* held to the
            # three currencies — `ck_daily_bonuses_currency` also permits the
            # locality and animal kinds handled below.
            balance_field = _CURRENCY_FIELD[currency]
            new_balance = ledger.grant(
                session, player, currency, offer.amount, "daily_bonus", ref_table="daily_bonuses", ref_id=offer.id
            )
        elif offer.currency == "animal":
            season = ensure_player_season(session, player)
            species = SPECIES_BY_CODE.get(offer.reward_code or "")
            if species is None:
                raise HTTPException(500, "У ежедневного бонуса потерялся вид животного")
            create_animal(
                session,
                player_id=player.id,
                season_id=season.id,
                origin="daily_bonus",
                genes=roll_genes(),
                habitat=roll_habitat(),
                species_id=SPECIES_ID_BY_CODE[species["code"]],
            )
            reward_name, reward_emoji = species["name"], species["emoji"]
        elif offer.currency == "locality":
            season = ensure_player_season(session, player)
            available = [
                habitat for habitat in HABITATS
                if session.scalar(select(Locality.id).where(
                    Locality.player_id == player.id,
                    Locality.season_id == season.id,
                    Locality.habitat == habitat,
                )) is None
            ]
            habitat = offer.reward_code if offer.reward_code in available else (available[0] if available else None)
            if habitat is None:
                raise HTTPException(400, "Все местности уже открыты")
            session.add(Locality(player_id=player.id, season_id=season.id, habitat=habitat, price_paid_rub=0))
            reward_name, reward_emoji = _HABITAT_REWARD_META[habitat]
        else:
            raise HTTPException(500, "Неизвестный тип ежедневного бонуса")
        offer.claimed_at = utcnow()

        result = {
            "ok": True,
            "currency": offer.currency,
            "amount": offer.amount,
            "reward_code": offer.reward_code,
            "reward_name": reward_name,
            "reward_emoji": reward_emoji,
        }
        if new_balance is not None and balance_field is not None:
            result[balance_field] = new_balance
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
            # The vet screen can outlive a refresh or another cure request. Treating this
            # as a successful no-op prevents a stale button from showing a false error.
            return {
                "ok": True,
                "cost_usd": 0,
                "new_usd": ledger.balance(player, "usd"),
                "income_rub_per_min": player.income_rub_per_min,
            }

        # Recompute the price server-side (never trust the client), using the same locality
        # habitat the client saw in the animal payload.
        locality_habitat = None
        if animal.locality_id is not None:
            locality_habitat = session.scalars(
                select(Locality.habitat).where(Locality.id == animal.locality_id)
            ).first()
        bonuses = bonuses_module.load(session, player.id)
        cost_usd = cure_cost_usd(animal, locality_habitat, bonuses, player.vet_level)

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


def cure_all_animals(tg_id: int) -> dict:
    """Cure every currently sick, live animal in one atomic purchase."""
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        animals = session.scalars(
            select(Animal)
            .where(Animal.player_id == player.id, alive_clause(), Animal.sick_since.is_not(None))
            .with_for_update()
        ).all()
        bonuses = bonuses_module.load(session, player.id)
        locality_habitats: dict[int, str] = {
            locality_id: habitat
            for locality_id, habitat in session.execute(
                select(Locality.id, Locality.habitat).where(Locality.player_id == player.id)
            ).all()
        }
        # An animal standing outside any enclosure has no habitat to match against, and
        # `locality_id` is nullable for exactly that case.
        total_cost = sum(
            cure_cost_usd(
                animal,
                locality_habitats.get(animal.locality_id) if animal.locality_id is not None else None,
                bonuses,
                player.vet_level,
            )
            for animal in animals
        )

        if total_cost:
            ledger.spend(session, player, "usd", total_cost, "cure_animal")
            for animal in animals:
                animal.sick_since = None
            sync_player_income(session, player, bonuses)

        result = {
            "ok": True,
            "cured_count": len(animals),
            "cost_usd": total_cost,
            "new_usd": ledger.balance(player, "usd"),
            "income_rub_per_min": player.income_rub_per_min,
        }
        session.commit()
        return result
