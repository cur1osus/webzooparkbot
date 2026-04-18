from __future__ import annotations

import random

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.core.errors import AppError
from api.app.models.pack import PackOpening
from api.app.models.player_season import PlayerSeason
from api.app.models.enums import PackOpeningType
from api.app.services.logic import current_season_day, create_pack_animal, next_paid_pack_price


def get_pack_state(db: Session, profile: PlayerSeason, now):
    season_day = current_season_day(profile.season, now)
    free_opened = (
        db.scalar(
            select(func.count(PackOpening.id)).where(
                PackOpening.player_season_id == profile.id,
                PackOpening.season_day == season_day,
                PackOpening.opening_type == PackOpeningType.FREE,
            )
        )
        or 0
    )
    paid_count = (
        db.scalar(
            select(func.count(PackOpening.id)).where(
                PackOpening.player_season_id == profile.id,
                PackOpening.season_day == season_day,
                PackOpening.opening_type == PackOpeningType.PAID,
            )
        )
        or 0
    )
    return {
        "season_day": season_day,
        "free_pack_available": free_opened == 0,
        "paid_packs_opened_today": int(paid_count),
        "next_paid_pack_price": next_paid_pack_price(int(paid_count)),
    }


def open_pack(db: Session, profile: PlayerSeason, now):
    state = get_pack_state(db, profile, now)
    opening_type = PackOpeningType.FREE if state["free_pack_available"] else PackOpeningType.PAID
    price_paid = 0 if opening_type == PackOpeningType.FREE else state["next_paid_pack_price"]
    if opening_type == PackOpeningType.PAID and profile.balance_coins < price_paid:
        raise AppError("Not enough coins to open another pack today", status_code=409)

    if opening_type == PackOpeningType.PAID:
        profile.balance_coins -= price_paid

    animal = create_pack_animal(profile, now, random.Random())
    db.add(animal)
    db.flush()

    opening = PackOpening(
        player_season=profile,
        season_day=state["season_day"],
        opening_type=opening_type,
        price_paid=price_paid,
        reward_animal=animal,
    )
    db.add(opening)
    db.flush()
    return opening
