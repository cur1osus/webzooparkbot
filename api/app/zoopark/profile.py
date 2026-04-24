from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

from api.app.zoopark.catalog import ANIMAL_BY_DB_ID, AVIARY_BY_DB_ID, DIVERSITY_BONUS_PER_SPECIES
from api.app.zoopark.db_tables import (
    ZOOPARK_ANIMALS_TABLE,
    ZOOPARK_AVIARIES_TABLE,
    ZOOPARK_EXTRA_TABLE,
    ZOOPARK_ITEMS_TABLE,
    ZOOPARK_SICK_EVENTS_TABLE,
    ZOOPARK_UNITY_TABLE,
    ZOOPARK_USERS_TABLE,
)


def get_user(cur, tg_id: int):
    cur.execute(f"SELECT * FROM {ZOOPARK_USERS_TABLE} WHERE id_user=%s", (tg_id,))
    return cur.fetchone()


def get_extra(cur, user_id: int) -> dict:
    cur.execute(f"SELECT * FROM {ZOOPARK_EXTRA_TABLE} WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if row:
        return row
    cur.execute(
        f"INSERT INTO {ZOOPARK_EXTRA_TABLE} (user_id, balance_seq, data_version) VALUES (%s,0,0)",
        (user_id,),
    )
    return {"user_id": user_id, "balance_seq": 0, "data_version": 0, "profile_emoji": None, "forge_sets_json": None}


def bump_data_version(cur, user_id: int) -> int:
    ts = int(time.time() * 1000)
    cur.execute(
        f"INSERT INTO {ZOOPARK_EXTRA_TABLE} (user_id, data_version) VALUES (%s,%s) "
        "ON DUPLICATE KEY UPDATE data_version=%s",
        (user_id, ts, ts),
    )
    return ts


def get_animals(cur, user_id: int) -> list[dict]:
    cur.execute(
        f"SELECT animal_info_id, quantity FROM {ZOOPARK_ANIMALS_TABLE} WHERE user_id=%s AND quantity>0",
        (user_id,),
    )
    result: list[dict] = []
    for row in cur.fetchall():
        animal = ANIMAL_BY_DB_ID.get(int(row["animal_info_id"]))
        if animal:
            result.append({"animal_id": animal["id"], "quantity": int(row["quantity"])})
    return result


def get_aviaries(cur, user_id: int) -> list[dict]:
    cur.execute(
        f"SELECT aviary_info_id, quantity FROM {ZOOPARK_AVIARIES_TABLE} WHERE user_id=%s AND quantity>0",
        (user_id,),
    )
    result: list[dict] = []
    for row in cur.fetchall():
        aviary = AVIARY_BY_DB_ID.get(int(row["aviary_info_id"]))
        if aviary:
            result.append({"aviary_id": aviary["id"], "count": int(row["quantity"])})
    return result


def get_sick(cur, user_id: int) -> list[dict]:
    cur.execute(f"SELECT animal_id, penalty_rub_per_min, since FROM {ZOOPARK_SICK_EVENTS_TABLE} WHERE user_id=%s", (user_id,))
    return [
        {
            "animal_id": row["animal_id"],
            "penalty_rub_per_min": int(row["penalty_rub_per_min"]),
            "since": row["since"].isoformat() if hasattr(row["since"], "isoformat") else str(row["since"]),
        }
        for row in cur.fetchall()
    ]


def get_forge_items(cur, user_id: int) -> list[dict]:
    cur.execute(f"SELECT id, emoji, name, lvl, properties, rarity, is_active FROM {ZOOPARK_ITEMS_TABLE} WHERE user_id=%s", (user_id,))
    result: list[dict] = []
    for row in cur.fetchall():
        try:
            raw = json.loads(row["properties"]) if row["properties"] else []
        except Exception:
            raw = []
        # Support old dict format (single property) → convert to list
        if isinstance(raw, dict):
            props: list[dict] = [{
                "type": raw.get("item_type", "income_boost"),
                "value": raw.get("effect_value", 0),
                "label": raw.get("effect_label", ""),
            }]
        else:
            props = raw if isinstance(raw, list) else []
        result.append({
            "id": str(row["id"]),
            "name": row["name"],
            "icon": row["emoji"],
            "rarity": row["rarity"],
            "level": int(row["lvl"]),
            "properties": props,
            "is_active": bool(row["is_active"]),
        })
    return result


def get_forge_sets(cur, user_id: int, items: list[dict] | None = None) -> list[dict]:
    extra = get_extra(cur, user_id)
    try:
        raw_sets = json.loads(extra.get("forge_sets_json") or "[]")
    except Exception:
        raw_sets = []
    if not isinstance(raw_sets, list):
        raw_sets = []

    owned_ids = {str(item["id"]) for item in items} if items is not None else None
    active_ids = {str(item["id"]) for item in items or [] if item.get("is_active")}
    result: list[dict] = []
    seen_ids: set[str] = set()

    for index, raw in enumerate(raw_sets, start=1):
        if not isinstance(raw, dict):
            continue
        set_id = str(raw.get("id") or index)
        if set_id in seen_ids:
            continue
        seen_ids.add(set_id)

        item_ids: list[str] = []
        for raw_id in raw.get("item_ids") or []:
            item_id = str(raw_id)
            if item_id in item_ids:
                continue
            if owned_ids is not None and item_id not in owned_ids:
                continue
            item_ids.append(item_id)
            if len(item_ids) >= 3:
                break

        result.append({
            "id": set_id,
            "name": str(raw.get("name") or f"Сет {index}")[:32],
            "icon": str(raw.get("icon") or "⚒️")[:8],
            "item_ids": item_ids,
            "is_active": bool(item_ids) and set(item_ids) == active_ids,
        })
    return result


def get_clan(cur, user_id: int, unity_id) -> dict | None:
    if not unity_id:
        return None
    cur.execute(f"SELECT * FROM {ZOOPARK_UNITY_TABLE} WHERE idpk=%s", (unity_id,))
    clan = cur.fetchone()
    if not clan:
        return None
    cur.execute(f"SELECT COUNT(*) AS cnt FROM {ZOOPARK_USERS_TABLE} WHERE unity_id=%s", (unity_id,))
    count = int(cur.fetchone()["cnt"])
    return {
        "id": clan["idpk"],
        "name": clan["name"],
        "level": int(clan["level"]),
        "member_count": count,
        "specialty": None,
        "role": "owner" if clan["owner_id"] == user_id else "member",
    }


def season_end() -> str:
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=30)
    return end.isoformat()


def build_state(cur, user: dict, income_rub_per_min: int) -> dict:
    uid = user["id"]
    extra = get_extra(cur, uid)
    animals = get_animals(cur, uid)
    aviaries = get_aviaries(cur, uid)
    sick = get_sick(cur, uid)
    forge = get_forge_items(cur, uid)
    forge_sets = get_forge_sets(cur, uid, forge)
    clan = get_clan(cur, uid, user.get("unity_id"))

    total_seats = sum(
        next(aviary["seats"] for aviary in AVIARY_BY_DB_ID.values() if aviary["id"] == aviary_state["aviary_id"]) * aviary_state["count"]
        for aviary_state in aviaries
    )
    occupied = sum(animal["quantity"] for animal in animals)

    return {
        "tg_id": int(user["id_user"]),
        "nickname": user["nickname"] or "",
        "registered_at": user["date_reg"].isoformat() if hasattr(user["date_reg"], "isoformat") else str(user["date_reg"]),
        "profile_emoji": extra.get("profile_emoji"),
        "rub": int(user["rub"]),
        "usd": int(user["usd"]),
        "paw_coins": int(user["paw_coins"]),
        "income_rub_per_min": income_rub_per_min,
        "expenses_rub_per_min": sum(item["penalty_rub_per_min"] for item in sick),
        "animals": animals,
        "aviaries": aviaries,
        "total_seats": total_seats,
        "free_seats": max(0, total_seats - occupied),
        "species_count": len(animals),
        "diversity_bonus_per_species": DIVERSITY_BONUS_PER_SPECIES,
        "sick_animals": sick,
        "forge_items": forge,
        "forge_sets": forge_sets,
        "clan": clan,
        "season_end": season_end(),
        "bonus": int(user["bonus"]),
        "balance_seq": int(extra.get("balance_seq", 0)),
        "data_version": int(extra.get("data_version", 0)),
    }
