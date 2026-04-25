from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from api.app.db.models import ForgeSet, ForgeSetItem, Item, Locality, PackAnimal, SickEvent, Unity, User
from api.app.zoopark.catalog import DIVERSITY_BONUS_PER_SPECIES
from api.app.zoopark.income import pack_animal_income
from api.app.zoopark.season import ensure_player_season


def get_user(session: Session, tg_id: int) -> User | None:
    return session.query(User).filter(User.id_user == tg_id).first()


def bump_data_version(session: Session, user_id: int) -> int:
    ts = int(time.time() * 1000)
    user = session.get(User, user_id)
    if user:
        user.data_version = ts
    return ts


def get_sick(session: Session, user_id: int) -> list[dict]:
    rows = session.query(SickEvent).filter(SickEvent.user_id == user_id).all()
    return [
        {
            "animal_id": str(row.animal_id),
            "penalty_rub_per_min": row.penalty_rub_per_min,
            "since": row.since.isoformat() if hasattr(row.since, "isoformat") else str(row.since),
        }
        for row in rows
    ]


def get_forge_items(session: Session, user_id: int) -> list[dict]:
    rows = session.query(Item).filter(Item.user_id == user_id).all()
    result: list[dict] = []
    for row in rows:
        try:
            raw = json.loads(row.properties) if row.properties else []
        except Exception:
            raw = []
        if isinstance(raw, dict):
            props: list[dict] = [{
                "type": raw.get("item_type", "income_boost"),
                "value": raw.get("effect_value", 0),
                "label": raw.get("effect_label", ""),
            }]
        else:
            props = raw if isinstance(raw, list) else []
        result.append({
            "id": str(row.id),
            "name": row.name,
            "icon": row.emoji,
            "rarity": row.rarity,
            "level": row.lvl,
            "properties": props,
            "is_active": bool(row.is_active),
        })
    return result


def get_forge_sets(session: Session, user_id: int, items: list[dict] | None = None) -> list[dict]:
    owned_ids = {str(item["id"]) for item in items} if items is not None else None
    active_ids = {str(item["id"]) for item in items or [] if item.get("is_active")}
    sets = (
        session.query(ForgeSet)
        .filter(ForgeSet.user_id == user_id)
        .order_by(ForgeSet.created_at.asc(), ForgeSet.id.asc())
        .all()
    )

    result: list[dict] = []
    for item_set in sets:
        links = (
            session.query(ForgeSetItem)
            .filter(ForgeSetItem.set_id == item_set.id)
            .order_by(ForgeSetItem.position.asc())
            .all()
        )
        item_ids: list[str] = []
        for link in links:
            item_id = str(link.item_id)
            if owned_ids is not None and item_id not in owned_ids:
                continue
            item_ids.append(item_id)

        result.append({
            "id": item_set.set_key,
            "name": item_set.name,
            "icon": item_set.icon,
            "item_ids": item_ids,
            "is_active": bool(item_ids) and set(item_ids) == active_ids,
        })
    return result


def get_clan(session: Session, user_id: int, unity_id) -> dict | None:
    if not unity_id:
        return None
    clan = session.get(Unity, unity_id)
    if not clan:
        return None
    count = session.query(User).filter(User.unity_id == unity_id).count()
    return {
        "id": clan.idpk,
        "name": clan.name,
        "level": clan.level,
        "member_count": count,
        "specialty": None,
        "role": "owner" if clan.owner_id == user_id else "member",
    }


def _pack_animal_state(animal: PackAnimal, locality_habitat: str | None = None) -> dict:
    habitat_bonus = 1.5 if locality_habitat and locality_habitat == animal.habitat else 1.0
    return {
        "id": animal.id,
        "animal_info_id": animal.animal_info_id,
        "survival": animal.survival,
        "reproduction": animal.reproduction,
        "appearance": animal.appearance,
        "size_trait": animal.size_trait,
        "habitat": animal.habitat,
        "source": animal.source,
        "acquired_at": animal.acquired_at.isoformat() if hasattr(animal.acquired_at, "isoformat") else str(animal.acquired_at),
        "dies_at": animal.dies_at.isoformat() if animal.dies_at and hasattr(animal.dies_at, "isoformat") else (str(animal.dies_at) if animal.dies_at else None),
        "locality_id": animal.locality_id,
        "can_breed": animal.last_bred_date != datetime.now(timezone.utc).date(),
        "income": pack_animal_income(animal, habitat_bonus),
        "habitat_bonus": habitat_bonus > 1.0,
    }


def get_live_pack_animals(session: Session, user_id: int, season_id: int) -> list[dict]:
    rows = (
        session.query(PackAnimal, Locality.habitat)
        .outerjoin(Locality, PackAnimal.locality_id == Locality.id)
        .filter(
            PackAnimal.user_id == user_id,
            PackAnimal.season_id == season_id,
            PackAnimal.is_alive == 1,
        )
        .order_by(PackAnimal.acquired_at.desc())
        .all()
    )
    return [_pack_animal_state(animal, habitat) for animal, habitat in rows]


def build_state(session: Session, user: User, income_rub_per_min: int) -> dict:
    uid = user.id
    season = ensure_player_season(session, user)
    sick = get_sick(session, uid)
    forge = get_forge_items(session, uid)
    forge_sets = get_forge_sets(session, uid, forge)
    clan = get_clan(session, uid, user.unity_id)
    pack_animals = get_live_pack_animals(session, uid, season.id)
    localities_count = session.query(Locality).filter(Locality.user_id == uid, Locality.season_id == season.id).count()

    return {
        "tg_id": user.id_user,
        "nickname": user.nickname or "",
        "registered_at": user.date_reg.isoformat() if hasattr(user.date_reg, "isoformat") else str(user.date_reg),
        "profile_emoji": user.profile_emoji,
        "rub": user.rub,
        "usd": user.usd,
        "paw_coins": user.paw_coins,
        "income_rub_per_min": income_rub_per_min,
        "expenses_rub_per_min": sum(item["penalty_rub_per_min"] for item in sick),
        "pack_animals": pack_animals,
        "animals": [],
        "aviaries": [],
        "total_seats": 0,
        "free_seats": 0,
        "species_count": len({animal["animal_info_id"] for animal in pack_animals}),
        "live_animals_count": len(pack_animals),
        "localities_count": localities_count,
        "season_id": season.id,
        "season_started_at": season.starts_at.isoformat() if hasattr(season.starts_at, "isoformat") else str(season.starts_at),
        "season_end": season.ends_at.isoformat() if hasattr(season.ends_at, "isoformat") else str(season.ends_at),
        "sick_animals": sick,
        "forge_items": forge,
        "forge_sets": forge_sets,
        "clan": clan,
        "bonus": user.bonus,
        "balance_seq": user.balance_seq or 0,
        "data_version": user.data_version or 0,
        "diversity_bonus_per_species": DIVERSITY_BONUS_PER_SPECIES,
    }
