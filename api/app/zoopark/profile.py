from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

from api.app.zoopark.catalog import ANIMAL_BY_DB_ID, AVIARY_BY_DB_ID, DIVERSITY_BONUS_PER_SPECIES


def get_user(cur, tg_id: int):
    cur.execute("SELECT * FROM users WHERE id_user=%s", (tg_id,))
    return cur.fetchone()


def get_extra(cur, user_id: int) -> dict:
    cur.execute("SELECT * FROM webapp_extra WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if row:
        return row
    cur.execute(
        "INSERT INTO webapp_extra (user_id, balance_seq, data_version) VALUES (%s,0,0)",
        (user_id,),
    )
    return {"user_id": user_id, "balance_seq": 0, "data_version": 0, "profile_emoji": None}


def bump_data_version(cur, user_id: int) -> int:
    ts = int(time.time() * 1000)
    cur.execute(
        "INSERT INTO webapp_extra (user_id, data_version) VALUES (%s,%s) "
        "ON DUPLICATE KEY UPDATE data_version=%s",
        (user_id, ts, ts),
    )
    return ts


def get_animals(cur, user_id: int) -> list[dict]:
    cur.execute(
        "SELECT animal_info_id, quantity FROM animals WHERE user_id=%s AND quantity>0",
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
        "SELECT aviary_info_id, quantity FROM aviaries WHERE user_id=%s AND quantity>0",
        (user_id,),
    )
    result: list[dict] = []
    for row in cur.fetchall():
        aviary = AVIARY_BY_DB_ID.get(int(row["aviary_info_id"]))
        if aviary:
            result.append({"aviary_id": aviary["id"], "count": int(row["quantity"])})
    return result


def get_sick(cur, user_id: int) -> list[dict]:
    cur.execute("SELECT animal_id, penalty_rub_per_min, since FROM sick_events WHERE user_id=%s", (user_id,))
    return [
        {
            "animal_id": row["animal_id"],
            "penalty_rub_per_min": int(row["penalty_rub_per_min"]),
            "since": row["since"].isoformat() if hasattr(row["since"], "isoformat") else str(row["since"]),
        }
        for row in cur.fetchall()
    ]


def get_forge_items(cur, user_id: int) -> list[dict]:
    cur.execute("SELECT id, emoji, name, lvl, properties, rarity, is_active FROM items WHERE user_id=%s", (user_id,))
    result: list[dict] = []
    for row in cur.fetchall():
        try:
            props = json.loads(row["properties"]) if row["properties"] else {}
        except Exception:
            props = {}
        result.append(
            {
                "id": str(row["id"]),
                "item_type": props.get("item_type", "unknown"),
                "name": row["name"],
                "icon": row["emoji"],
                "rarity": row["rarity"],
                "level": int(row["lvl"]),
                "effect_label": props.get("effect_label", ""),
                "effect_value": props.get("effect_value", 0),
                "sv": props.get("sv", 0),
                "is_active": bool(row["is_active"]),
            }
        )
    return result


def get_clan(cur, user_id: int, unity_id) -> dict | None:
    if not unity_id:
        return None
    cur.execute("SELECT * FROM unity WHERE idpk=%s", (unity_id,))
    clan = cur.fetchone()
    if not clan:
        return None
    cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE unity_id=%s", (unity_id,))
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
        "forge_sets": [],
        "clan": clan,
        "season_end": season_end(),
        "bonus": int(user["bonus"]),
        "balance_seq": int(extra.get("balance_seq", 0)),
        "data_version": int(extra.get("data_version", 0)),
    }
