from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import BreedingEvent, Expedition, ExpeditionAnimal, Locality, PackAnimal, PackOpening, User
from api.app.schemas.progression import AssignLocalityBody, BreedBody, BuyLocalityBody, StartExpeditionBody
from api.app.zoopark.catalog import ANIMALS
from api.app.zoopark.income import pack_animal_income, sync_passive_balance
from api.app.zoopark.profile import get_user
from api.app.zoopark.season import ensure_player_season


PACK_PROPERTIES = ["low", "low", "low", "low", "medium", "medium", "medium", "medium", "high", "high"]
HABITATS = ["desert", "mountains", "forest", "fields", "antarctica"]
PACK_BASE_PRICE = 2000
PACK_MULTIPLIER = 2.0
PACK_SURVIVAL_DAYS = {"low": 4, "medium": 8, "high": 15}
LOCALITY_BASE_PRICE = 50_000
BREED_RATES: dict[tuple[str, str], float] = {
    ("low", "low"): 0.30,
    ("low", "medium"): 0.45,
    ("medium", "low"): 0.45,
    ("medium", "medium"): 0.60,
    ("medium", "high"): 0.75,
    ("high", "medium"): 0.75,
    ("high", "high"): 0.90,
}
TRAIT_TIERS = {"low": 0, "medium": 1, "high": 2}
COMBAT_TIERS: dict[str, int] = {"low": 1, "medium": 2, "high": 3}
EXPEDITION_PARAMS: dict[str, dict] = {
    "fields": {"minutes": 60, "chances": [0.25, 0.45, 0.30]},
    "desert": {"minutes": 120, "chances": [0.20, 0.45, 0.35]},
    "forest": {"minutes": 150, "chances": [0.20, 0.45, 0.35]},
    "mountains": {"minutes": 180, "chances": [0.15, 0.45, 0.40]},
    "antarctica": {"minutes": 240, "chances": [0.10, 0.45, 0.45]},
}


def locality_next_price(count_owned: int) -> int:
    if count_owned == 0:
        return 0
    return int(LOCALITY_BASE_PRICE * (1.5 ** (count_owned - 1)))


def breed_trait(trait1: str, trait2: str) -> str:
    if trait1 == trait2:
        return trait1
    worse = trait1 if TRAIT_TIERS[trait1] < TRAIT_TIERS[trait2] else trait2
    better = trait2 if TRAIT_TIERS[trait1] < TRAIT_TIERS[trait2] else trait1
    return worse if random.random() < 0.6 else better


def ensure_first_locality(session: Session, user_id: int, season_id: int) -> None:
    count = session.query(Locality).filter(Locality.user_id == user_id, Locality.season_id == season_id).count()
    if count == 0:
        session.add(Locality(
            user_id=user_id, season_id=season_id, habitat=random.choice(HABITATS),
            created_at=datetime.now(timezone.utc),
        ))
        session.flush()


def pack_next_price(packs_today: int) -> int:
    if packs_today == 0:
        return 0
    return int(PACK_BASE_PRICE * (PACK_MULTIPLIER ** (packs_today - 1)))


def roll_pack_animal() -> dict:
    return {
        "survival": random.choice(PACK_PROPERTIES),
        "reproduction": random.choice(PACK_PROPERTIES),
        "appearance": random.choice(PACK_PROPERTIES),
        "size_trait": random.choice(PACK_PROPERTIES),
        "habitat": random.choice(HABITATS),
    }


def get_pack_state(session: Session, user_id: int, season_id: int) -> tuple[int, bool]:
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    count = session.query(PackOpening).filter(
        PackOpening.user_id == user_id,
        PackOpening.season_id == season_id,
        PackOpening.opened_at >= start,
        PackOpening.opened_at < end,
    ).count()
    return count, count > 0


def random_animal_info_id() -> int:
    return random.randint(1, len(ANIMALS))


def active_expedition_animal_ids(session: Session):
    return (
        session.query(ExpeditionAnimal.animal_id)
        .join(Expedition, Expedition.id == ExpeditionAnimal.expedition_id)
        .filter(Expedition.status == "active")
        .subquery()
    )


def expire_dead_pack_animals(session: Session, user_id: int) -> None:
    now = datetime.now(timezone.utc)
    session.query(PackAnimal).filter(
        PackAnimal.user_id == user_id,
        PackAnimal.is_alive == 1,
        PackAnimal.dies_at.isnot(None),
        PackAnimal.dies_at <= now,
    ).update({"is_alive": 0})


def format_pack_animal(animal: PackAnimal, locality_habitat: str | None = None) -> dict:
    habitat_bonus = 1.5 if locality_habitat and locality_habitat == animal.habitat else 1.0
    return {
        "id": animal.id,
        "animal_info_id": getattr(animal, "animal_info_id", None),
        "survival": animal.survival,
        "reproduction": animal.reproduction,
        "appearance": animal.appearance,
        "size_trait": animal.size_trait,
        "habitat": animal.habitat,
        "source": getattr(animal, "source", "pack"),
        "acquired_at": animal.acquired_at.isoformat() if hasattr(animal.acquired_at, "isoformat") else str(animal.acquired_at),
        "dies_at": animal.dies_at.isoformat() if animal.dies_at and hasattr(animal.dies_at, "isoformat") else (str(animal.dies_at) if animal.dies_at else None),
        "locality_id": animal.locality_id,
        "can_breed": animal.last_bred_date != datetime.now(timezone.utc).date(),
        "income": pack_animal_income(animal, habitat_bonus),
        "habitat_bonus": habitat_bonus > 1.0,
    }


def animal_combat_power(animal: PackAnimal) -> int:
    return COMBAT_TIERS[animal.size_trait] * 3 + COMBAT_TIERS[animal.survival] * 2 + COMBAT_TIERS[animal.appearance]


def roll_trait_weighted(chances: list[float]) -> str:
    roll = random.random()
    if roll < chances[0]:
        return "low"
    if roll < chances[0] + chances[1]:
        return "medium"
    return "high"


def resolve_expedition(session: Session, expedition_id: int, habitat: str, user_id: int, season_id: int) -> dict:
    squad = (
        session.query(PackAnimal)
        .join(ExpeditionAnimal, ExpeditionAnimal.animal_id == PackAnimal.id)
        .filter(ExpeditionAnimal.expedition_id == expedition_id)
        .all()
    )
    squad_power = sum(animal_combat_power(animal) for animal in squad)

    chances = EXPEDITION_PARAMS[habitat]["chances"]
    wild_props = {
        "survival": roll_trait_weighted(chances),
        "reproduction": roll_trait_weighted(chances),
        "appearance": roll_trait_weighted(chances),
        "size_trait": roll_trait_weighted(chances),
        "habitat": habitat,
    }
    wild_power = COMBAT_TIERS[wild_props["size_trait"]] * 3 + COMBAT_TIERS[wild_props["survival"]] * 2 + COMBAT_TIERS[wild_props["appearance"]]
    result: dict[str, object] = {"squad_power": squad_power, "wild_power": wild_power, "wild": wild_props}

    if squad_power >= wild_power:
        dies_at = datetime.now(timezone.utc) + timedelta(days=PACK_SURVIVAL_DAYS[wild_props["survival"]])
        new_animal = PackAnimal(
            user_id=user_id,
            season_id=season_id,
            animal_info_id=random_animal_info_id(),
            survival=wild_props["survival"],
            reproduction=wild_props["reproduction"],
            appearance=wild_props["appearance"],
            size_trait=wild_props["size_trait"],
            habitat=wild_props["habitat"],
            source="expedition",
            dies_at=dies_at,
            acquired_at=datetime.now(timezone.utc),
        )
        session.add(new_animal)
        session.flush()
        result["outcome"] = "victory"
        result["reward_animal_id"] = new_animal.id
    else:
        alive_squad = [animal for animal in squad if animal.is_alive]
        killed_id = None
        if alive_squad:
            victim = random.choice(alive_squad)
            victim.is_alive = 0
            killed_id = victim.id
        result["outcome"] = "defeat"
        result["killed_id"] = killed_id

    expedition = session.get(Expedition, expedition_id)
    if expedition:
        expedition.status = "finished"
        expedition.result_json = json.dumps(result)
    return result


def format_expedition_dt(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        result = value.isoformat()
        if "+" not in result and "Z" not in result and not result.endswith("+00:00"):
            result += "+00:00"
        return result
    return str(value)


def api_packs_info(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")

        season = ensure_player_season(session, user)
        packs_today, _ = get_pack_state(session, user.id, season.id)
        expire_dead_pack_animals(session, user.id)
        active_ids = active_expedition_animal_ids(session)
        animals = (
            session.query(PackAnimal)
            .filter(
                PackAnimal.user_id == user.id,
                PackAnimal.season_id == season.id,
                PackAnimal.is_alive == 1,
                PackAnimal.id.not_in(active_ids),
            )
            .order_by(PackAnimal.acquired_at.desc())
            .all()
        )
        return {
            "packs_today": packs_today,
            "free_available": packs_today == 0,
            "next_price": pack_next_price(packs_today),
            "animals": [format_pack_animal(a) for a in animals],
        }


def api_packs_open(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)
        season = ensure_player_season(session, user)

        rub = user.rub
        packs_today, _date_is_today = get_pack_state(session, user.id, season.id)
        price = pack_next_price(packs_today)
        if price > 0 and rub < price:
            raise HTTPException(400, f"Недостаточно ₽ (нужно {price})")

        if price > 0:
            user.rub -= price

        props = roll_pack_animal()
        dies_at = datetime.now(timezone.utc) + timedelta(days=PACK_SURVIVAL_DAYS[props["survival"]])
        now = datetime.now(timezone.utc)
        new_animal = PackAnimal(
            user_id=user.id,
            season_id=season.id,
            animal_info_id=random_animal_info_id(),
            survival=props["survival"],
            reproduction=props["reproduction"],
            appearance=props["appearance"],
            size_trait=props["size_trait"],
            habitat=props["habitat"],
            source="pack",
            dies_at=dies_at,
            acquired_at=now,
        )
        session.add(new_animal)
        session.flush()
        animal_id = new_animal.id

        new_count = packs_today + 1
        session.add(PackOpening(
            user_id=user.id,
            season_id=season.id,
            animal_id=animal_id,
            opened_at=now,
            price_paid=price,
            is_free=price == 0,
        ))

        session.commit()
        return {
            "ok": True,
            "price_paid": price,
            "new_rub": user.rub,
            "packs_today": new_count,
            "next_price": pack_next_price(new_count),
            "animal": {
                "id": animal_id,
                **props,
                "acquired_at": now.isoformat(),
                "dies_at": dies_at.isoformat(),
                "locality_id": None,
                "can_breed": True,
                "income": pack_animal_income(new_animal),
            },
        }


def api_get_localities(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")

        season = ensure_player_season(session, user)
        ensure_first_locality(session, user.id, season.id)
        localities_raw = (
            session.query(Locality)
            .filter(Locality.user_id == user.id, Locality.season_id == season.id)
            .order_by(Locality.created_at)
            .all()
        )
        expire_dead_pack_animals(session, user.id)
        active_ids = active_expedition_animal_ids(session)
        animals_raw = (
            session.query(PackAnimal)
            .filter(
                PackAnimal.user_id == user.id,
                PackAnimal.season_id == season.id,
                PackAnimal.is_alive == 1,
                PackAnimal.id.not_in(active_ids),
            )
            .order_by(PackAnimal.acquired_at.desc())
            .all()
        )
        session.commit()

        buckets: dict[int | None, list[PackAnimal]] = {loc.id: [] for loc in localities_raw}
        buckets[None] = []
        for animal in animals_raw:
            key = animal.locality_id if animal.locality_id in buckets else None
            buckets[key].append(animal)

        return {
            "localities": [
                {
                    "id": loc.id,
                    "habitat": loc.habitat,
                    "animals": [format_pack_animal(a, loc.habitat) for a in buckets[loc.id]],
                }
                for loc in localities_raw
            ],
            "unassigned": [format_pack_animal(a) for a in buckets[None]],
            "next_price": locality_next_price(len(localities_raw)) if len(localities_raw) < 5 else None,
            "habitats_taken": [loc.habitat for loc in localities_raw],
        }


def api_buy_locality(tg_id: int, body: BuyLocalityBody):
    if body.habitat not in HABITATS:
        raise HTTPException(400, "Неверная среда обитания")

    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)
        season = ensure_player_season(session, user)

        localities = session.query(Locality).filter(Locality.user_id == user.id, Locality.season_id == season.id).all()
        count = len(localities)
        taken = [loc.habitat for loc in localities]

        if count >= 5:
            raise HTTPException(400, "Достигнут максимум местностей (5)")
        if body.habitat in taken:
            raise HTTPException(400, "Эта местность уже открыта")

        price = locality_next_price(count)
        if price > 0 and user.rub < price:
            raise HTTPException(400, f"Недостаточно ₽ (нужно {price:,})")

        if price > 0:
            user.rub -= price

        new_loc = Locality(user_id=user.id, season_id=season.id, habitat=body.habitat, created_at=datetime.now(timezone.utc))
        session.add(new_loc)
        session.flush()
        locality_id = new_loc.id
        session.commit()
        return {"ok": True, "id": locality_id, "habitat": body.habitat, "price_paid": price, "new_rub": user.rub}


def api_assign_locality(tg_id: int, body: AssignLocalityBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, user)

        animal = session.query(PackAnimal).filter(
            PackAnimal.id == body.animal_id,
            PackAnimal.user_id == user.id,
            PackAnimal.season_id == season.id,
            PackAnimal.is_alive == 1,
        ).first()
        if not animal:
            raise HTTPException(404, "Животное не найдено")

        if body.locality_id is not None:
            loc = session.query(Locality).filter(
                Locality.id == body.locality_id, Locality.user_id == user.id, Locality.season_id == season.id
            ).first()
            if not loc:
                raise HTTPException(404, "Местность не найдена")

        animal.locality_id = body.locality_id
        session.commit()
        return {"ok": True}


def api_breed(tg_id: int, body: BreedBody):
    if body.animal_id_1 == body.animal_id_2:
        raise HTTPException(400, "Нельзя скрещивать животное с самим собой")

    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, user)

        today = datetime.now(timezone.utc).date()
        active_ids = active_expedition_animal_ids(session)
        animals = (
            session.query(PackAnimal)
            .filter(
                PackAnimal.id.in_([body.animal_id_1, body.animal_id_2]),
                PackAnimal.user_id == user.id,
                PackAnimal.season_id == season.id,
                PackAnimal.is_alive == 1,
                PackAnimal.id.not_in(active_ids),
            )
            .all()
        )
        by_id = {a.id: a for a in animals}
        if len(by_id) != 2:
            raise HTTPException(404, "Одно или оба животных не найдены")

        parent1 = by_id[body.animal_id_1]
        parent2 = by_id[body.animal_id_2]
        for parent in (parent1, parent2):
            if parent.last_bred_date == today:
                raise HTTPException(400, "Одно из животных уже скрещивалось сегодня")

        rate = BREED_RATES.get(
            (parent1.reproduction, parent2.reproduction),
            BREED_RATES.get((parent2.reproduction, parent1.reproduction), 0.60),
        )
        success = random.random() < rate
        parent1.last_bred_date = today
        parent2.last_bred_date = today

        offspring = None
        if success:
            props = {
                "survival": breed_trait(parent1.survival, parent2.survival),
                "reproduction": breed_trait(parent1.reproduction, parent2.reproduction),
                "appearance": breed_trait(parent1.appearance, parent2.appearance),
                "size_trait": breed_trait(parent1.size_trait, parent2.size_trait),
                "habitat": random.choice([parent1.habitat, parent2.habitat]),
            }
            dies_at = datetime.now(timezone.utc) + timedelta(days=PACK_SURVIVAL_DAYS[props["survival"]])
            now = datetime.now(timezone.utc)
            new_animal = PackAnimal(
                user_id=user.id,
                season_id=season.id,
                animal_info_id=random.choice([parent1.animal_info_id, parent2.animal_info_id]),
                survival=props["survival"],
                reproduction=props["reproduction"],
                appearance=props["appearance"],
                size_trait=props["size_trait"],
                habitat=props["habitat"],
                source="breeding",
                parent_1_id=parent1.id,
                parent_2_id=parent2.id,
                dies_at=dies_at,
                acquired_at=now,
            )
            session.add(new_animal)
            session.flush()
            offspring = {
                "id": new_animal.id,
                **props,
                "acquired_at": now.isoformat(),
                "dies_at": dies_at.isoformat(),
                "locality_id": None,
                "can_breed": False,
                "habitat_bonus": False,
                "income": pack_animal_income(new_animal),
            }
        session.add(BreedingEvent(
            user_id=user.id,
            season_id=season.id,
            parent_1_id=parent1.id,
            parent_2_id=parent2.id,
            child_id=new_animal.id if success and offspring else None,
            success_rate=int(rate * 100),
            success=1 if success else 0,
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()
        return {"ok": True, "success": success, "rate": rate, "animal": offspring}


def api_get_expeditions(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, user)

        localities = (
            session.query(Locality)
            .filter(Locality.user_id == user.id, Locality.season_id == season.id)
            .order_by(Locality.created_at)
            .all()
        )
        localities_out = [{"id": loc.id, "habitat": loc.habitat} for loc in localities]

        expedition = (
            session.query(Expedition)
            .filter(
                Expedition.user_id == user.id,
                Expedition.season_id == season.id,
                (Expedition.status == "active") | ((Expedition.status == "finished") & (Expedition.result_seen == 0)),
            )
            .order_by(Expedition.started_at.desc())
            .first()
        )
        active = None

        if expedition:
            expedition_id = expedition.id
            expedition_habitat = expedition.locality.habitat
            if expedition.status == "active":
                ends_at = expedition.ends_at
                if hasattr(ends_at, "tzinfo") and ends_at.tzinfo is None:
                    ends_at = ends_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) >= ends_at:
                    resolve_expedition(session, expedition_id, expedition_habitat, user.id, season.id)
                    session.flush()
                    session.refresh(expedition)

            squad = (
                session.query(PackAnimal)
                .join(ExpeditionAnimal, ExpeditionAnimal.animal_id == PackAnimal.id)
                .filter(ExpeditionAnimal.expedition_id == expedition_id)
                .all()
            )

            result_data = None
            if expedition.status == "finished" and expedition.result_json:
                result_data = json.loads(expedition.result_json)
                if result_data.get("outcome") == "victory" and result_data.get("reward_animal_id"):
                    reward = session.get(PackAnimal, result_data["reward_animal_id"])
                    if reward:
                        result_data["captured_animal"] = format_pack_animal(reward)

            active = {
                "id": expedition_id,
                "habitat": expedition_habitat,
                "started_at": format_expedition_dt(expedition.started_at),
                "ends_at": format_expedition_dt(expedition.ends_at),
                "status": expedition.status,
                "animals": [format_pack_animal(a) for a in squad],
                "result": result_data,
            }

        expire_dead_pack_animals(session, user.id)
        active_ids = active_expedition_animal_ids(session)
        available_animals = (
            session.query(PackAnimal)
            .filter(
                PackAnimal.user_id == user.id,
                PackAnimal.season_id == season.id,
                PackAnimal.is_alive == 1,
                PackAnimal.id.not_in(active_ids),
            )
            .order_by(PackAnimal.acquired_at.desc())
            .all()
        )
        session.commit()
        return {
            "active": active,
            "localities": localities_out,
            "available_animals": [format_pack_animal(a) for a in available_animals],
            "expedition_minutes": {habitat: params["minutes"] for habitat, params in EXPEDITION_PARAMS.items()},
        }


def api_start_expedition(tg_id: int, body: StartExpeditionBody):
    if not (3 <= len(body.animal_ids) <= 5):
        raise HTTPException(400, "Отряд: 3–5 животных")

    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, user)

        existing = session.query(Expedition).filter(
            Expedition.user_id == user.id,
            Expedition.season_id == season.id,
            (Expedition.status == "active") | ((Expedition.status == "finished") & (Expedition.result_seen == 0)),
        ).first()
        if existing:
            raise HTTPException(400, "Уже есть активная или незавершённая экспедиция")

        locality = session.query(Locality).filter(
            Locality.id == body.locality_id, Locality.user_id == user.id, Locality.season_id == season.id
        ).first()
        if not locality:
            raise HTTPException(404, "Местность не найдена")

        valid_animals = (
            session.query(PackAnimal)
            .filter(
                PackAnimal.id.in_(body.animal_ids),
                PackAnimal.user_id == user.id,
                PackAnimal.season_id == season.id,
                PackAnimal.is_alive == 1,
                PackAnimal.id.not_in(active_expedition_animal_ids(session)),
            )
            .all()
        )
        if len(valid_animals) != len(body.animal_ids):
            raise HTTPException(400, "Некоторые животные недоступны")

        now = datetime.now(timezone.utc)
        ends_at = now + timedelta(minutes=EXPEDITION_PARAMS[locality.habitat]["minutes"])
        expedition = Expedition(
            user_id=user.id,
            season_id=season.id,
            locality_id=locality.id,
            started_at=now,
            ends_at=ends_at,
        )
        session.add(expedition)
        session.flush()
        expedition_id = expedition.id

        for animal_id in body.animal_ids:
            session.add(ExpeditionAnimal(expedition_id=expedition_id, animal_id=animal_id))

        session.commit()
        return {
            "ok": True,
            "expedition": {
                "id": expedition_id,
                "habitat": locality.habitat,
                "started_at": format_expedition_dt(now),
                "ends_at": format_expedition_dt(ends_at),
                "status": "active",
                "animals": [format_pack_animal(a) for a in valid_animals],
                "result": None,
            },
        }


def api_finish_expedition(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, user)

        expedition = (
            session.query(Expedition)
            .filter(Expedition.user_id == user.id, Expedition.season_id == season.id, Expedition.status == "active")
            .order_by(Expedition.started_at.desc())
            .first()
        )
        if not expedition:
            raise HTTPException(400, "Нет активной экспедиции")

        ends_at = expedition.ends_at
        if hasattr(ends_at, "tzinfo") and ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < ends_at:
            raise HTTPException(400, "Экспедиция ещё не завершена")

        result = resolve_expedition(session, expedition.id, expedition.locality.habitat, user.id, season.id)
        session.commit()

        if result.get("outcome") == "victory" and result.get("reward_animal_id"):
            reward = session.get(PackAnimal, result["reward_animal_id"])
            if reward:
                result["captured_animal"] = format_pack_animal(reward)

        return {"ok": True, "result": result}


def api_dismiss_expedition(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, user)
        session.query(Expedition).filter(
            Expedition.user_id == user.id,
            Expedition.season_id == season.id,
            Expedition.status == "finished",
            Expedition.result_seen == 0,
        ).update({"result_seen": 1})
        session.commit()
        return {"ok": True}
