from __future__ import annotations

from datetime import datetime, timezone
from math import trunc

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.app.db.models import Expedition, ExpeditionAnimal, Locality, PackAnimal, SickEvent, User

PACK_BASE_INCOME = 5000

PACK_INCOME_MULT = {
    "survival": {"low": 0.7, "medium": 1.0, "high": 1.3},
    "appearance": {"low": 0.6, "medium": 1.0, "high": 1.5},
    "size_trait": {"low": 0.8, "medium": 1.0, "high": 1.4},
}


def pack_animal_income(animal, habitat_bonus: float = 1.0) -> int:
    return int(
        PACK_BASE_INCOME
        * PACK_INCOME_MULT["survival"][animal.survival]
        * PACK_INCOME_MULT["appearance"][animal.appearance]
        * PACK_INCOME_MULT["size_trait"][animal.size_trait]
        * habitat_bonus
    )


def calc_sick_expenses(session: Session, user_id: int) -> int:
    total = session.query(func.coalesce(func.sum(SickEvent.penalty_rub_per_min), 0)).filter(
        SickEvent.user_id == user_id
    ).scalar()
    return int(total or 0)


def accrue_income(session: Session, user: User, income_rub_per_min: int, expenses_rub_per_min: int = 0) -> User:
    now = datetime.now(timezone.utc)
    last_income_at = getattr(user, "last_income_at", None)
    net_rub_per_min = income_rub_per_min - expenses_rub_per_min

    accrued = 0
    if last_income_at is not None and net_rub_per_min != 0:
        if hasattr(last_income_at, "tzinfo") and last_income_at.tzinfo is None:
            last_income_at = last_income_at.replace(tzinfo=timezone.utc)
        elapsed_mins = (now - last_income_at).total_seconds() / 60.0
        accrued = trunc(elapsed_mins * net_rub_per_min)

    new_rub = max(0, user.rub + accrued)
    new_seq = int(now.timestamp() * 1000)

    if new_rub != user.rub:
        user.rub = new_rub
    user.last_income_at = now
    user.balance_seq = new_seq

    return user


def calc_pack_income(session: Session, user_id: int, season_id: int | None = None) -> int:
    filters = [
        PackAnimal.user_id == user_id,
        PackAnimal.is_alive == 1,
        (PackAnimal.dies_at.is_(None)) | (PackAnimal.dies_at > func.now()),
    ]
    if season_id is not None:
        filters.append(PackAnimal.season_id == season_id)
    active_expedition_animals = (
        session.query(ExpeditionAnimal.animal_id)
        .join(Expedition, Expedition.id == ExpeditionAnimal.expedition_id)
        .filter(Expedition.status == "active")
        .subquery()
    )
    filters.append(PackAnimal.id.not_in(active_expedition_animals))

    rows = (
        session.query(PackAnimal, Locality.habitat)
        .outerjoin(Locality, PackAnimal.locality_id == Locality.id)
        .filter(*filters)
        .all()
    )
    total = 0
    for pack_animal, locality_habitat in rows:
        bonus = 1.5 if locality_habitat and locality_habitat == pack_animal.habitat else 1.0
        total += pack_animal_income(pack_animal, bonus)
    return total


def sync_passive_balance(session: Session, user: User) -> tuple[User, int, int]:
    income_rub_per_min = calc_pack_income(session, user.id)
    expenses_rub_per_min = calc_sick_expenses(session, user.id)
    return accrue_income(session, user, income_rub_per_min, expenses_rub_per_min), income_rub_per_min, expenses_rub_per_min
