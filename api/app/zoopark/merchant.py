from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import Merchant, PackAnimal
from api.app.zoopark.catalog import ANIMALS, ANIMAL_BY_DB_ID, ANIMAL_STRING_TO_DB
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import bump_data_version, get_user
from api.app.zoopark.progression import HABITATS, PACK_PROPERTIES, PACK_SURVIVAL_DAYS, format_pack_animal
from api.app.zoopark.season import ensure_player_season


def _roll_offer_traits() -> dict[str, str]:
    return {
        "survival": random.choice(PACK_PROPERTIES),
        "reproduction": random.choice(PACK_PROPERTIES),
        "appearance": random.choice(PACK_PROPERTIES),
        "size_trait": random.choice(PACK_PROPERTIES),
        "habitat": random.choice(HABITATS),
    }


def ensure_merchant(session: Session, user_id: int, season_id: int) -> list[Merchant]:
    now = datetime.now(timezone.utc)
    existing = (
        session.query(Merchant)
        .filter(Merchant.user_id == user_id, Merchant.season_id == season_id, Merchant.expires_at > now)
        .order_by(Merchant.id.asc())
        .all()
    )
    if existing:
        return existing

    session.query(Merchant).filter(Merchant.user_id == user_id, Merchant.season_id == season_id).delete()
    picks = random.sample(ANIMALS, min(3, len(ANIMALS)))
    expires_at = now + timedelta(hours=24)
    for pick in picks:
        discount = random.choice([5, 10, 15, 20, 25, 30])
        discounted = int(pick["price"] * (1 - discount / 100))
        session.add(Merchant(
            user_id=user_id,
            season_id=season_id,
            animal_info_id=ANIMAL_STRING_TO_DB[pick["id"]],
            **_roll_offer_traits(),
            discount=discount,
            price=pick["price"],
            price_with_discount=discounted,
            bought=0,
            created_at=now,
            expires_at=expires_at,
        ))
    session.flush()
    return (
        session.query(Merchant)
        .filter(Merchant.user_id == user_id, Merchant.season_id == season_id, Merchant.expires_at > now)
        .order_by(Merchant.id.asc())
        .all()
    )


def do_merchant_buy(tg_id: int, slot: int) -> dict:
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)
        season = ensure_player_season(session, user)

        offers = ensure_merchant(session, user.id, season.id)
        if slot < 1 or slot > len(offers):
            raise HTTPException(400, "Неверный слот")

        offer = offers[slot - 1]
        if offer.bought:
            raise HTTPException(400, "Уже куплено")

        animal_def = ANIMAL_BY_DB_ID.get(offer.animal_info_id)
        if not animal_def:
            raise HTTPException(400, "Животное не найдено")

        cost = offer.price_with_discount or animal_def["price"]
        if user.rub < cost:
            raise HTTPException(400, "Недостаточно рублей")

        now = datetime.now(timezone.utc)
        new_animal = PackAnimal(
            user_id=user.id,
            season_id=season.id,
            animal_info_id=offer.animal_info_id,
            survival=offer.survival,
            reproduction=offer.reproduction,
            appearance=offer.appearance,
            size_trait=offer.size_trait,
            habitat=offer.habitat,
            source="merchant",
            dies_at=now + timedelta(days=PACK_SURVIVAL_DAYS[offer.survival]),
            acquired_at=now,
        )
        session.add(new_animal)
        session.flush()

        user.rub -= cost
        offer.bought = 1
        bump_data_version(session, user.id)
        animal_payload = format_pack_animal(new_animal)
        session.commit()
        return {"ok": True, "new_rub": user.rub, "animal": animal_payload}


def get_merchant_animals(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, user)
        offers = ensure_merchant(session, user.id, season.id)
        session.commit()

        animals: list[dict] = []
        refreshes_at = None
        for index, offer in enumerate(offers[:3]):
            animal_def = ANIMAL_BY_DB_ID.get(offer.animal_info_id)
            if not animal_def:
                continue
            refreshes_at = offer.expires_at
            animals.append({
                "slot": index + 1,
                "animal_id": animal_def["id"],
                "animal_info_id": offer.animal_info_id,
                "quantity": 1,
                "original_price": offer.price or animal_def["price"],
                "discount_pct": offer.discount or 0,
                "final_price": offer.price_with_discount or animal_def["price"],
                "survival": offer.survival,
                "reproduction": offer.reproduction,
                "appearance": offer.appearance,
                "size_trait": offer.size_trait,
                "habitat": offer.habitat,
                "bought": bool(offer.bought),
            })

        if refreshes_at is None:
            refreshes_at = datetime.now(timezone.utc) + timedelta(hours=24)
        return {
            "animals": animals,
            "refreshes_at": refreshes_at.isoformat() if hasattr(refreshes_at, "isoformat") else str(refreshes_at),
        }


def buy_merchant_offer(tg_id: int, slot: int):
    return do_merchant_buy(tg_id, slot)
