from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from api.app.db.connection import get_db
from api.app.db.tables import (
    ZOOPARK_EXPEDITION_ANIMALS_TABLE,
    ZOOPARK_EXPEDITIONS_TABLE,
    ZOOPARK_EXTRA_TABLE,
    ZOOPARK_LOCALITIES_TABLE,
    ZOOPARK_PACK_ANIMALS_TABLE,
    ZOOPARK_USERS_TABLE,
)
from api.app.schemas.progression import AssignLocalityBody, BreedBody, BuyLocalityBody, StartExpeditionBody
from api.app.zoopark.income import pack_animal_income, sync_passive_balance
from api.app.zoopark.profile import get_user


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


def ensure_first_locality(cur, user_id: int) -> None:
    cur.execute(f"SELECT COUNT(*) AS cnt FROM {ZOOPARK_LOCALITIES_TABLE} WHERE user_id=%s", (user_id,))
    if cur.fetchone()["cnt"] == 0:
        cur.execute(f"INSERT INTO {ZOOPARK_LOCALITIES_TABLE} (user_id, habitat) VALUES (%s,%s)", (user_id, random.choice(HABITATS)))


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


def get_pack_state(cur, user_id: int) -> tuple[int, bool]:
    cur.execute(f"SELECT packs_today, packs_today_date FROM {ZOOPARK_EXTRA_TABLE} WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        return 0, False

    today = datetime.now(timezone.utc).date()
    stored_date = row["packs_today_date"]
    if stored_date is None or stored_date != today:
        return 0, False
    return int(row["packs_today"] or 0), True


def expire_dead_pack_animals(cur, user_id: int) -> None:
    cur.execute(
        f"UPDATE {ZOOPARK_PACK_ANIMALS_TABLE} SET is_alive=0 WHERE user_id=%s AND is_alive=1 AND dies_at IS NOT NULL AND dies_at <= NOW()",
        (user_id,),
    )


def format_pack_animal(row: dict, locality_habitat: str | None = None) -> dict:
    habitat_bonus = 1.5 if locality_habitat and locality_habitat == row["habitat"] else 1.0
    return {
        "id": row["id"],
        "survival": row["survival"],
        "reproduction": row["reproduction"],
        "appearance": row["appearance"],
        "size_trait": row["size_trait"],
        "habitat": row["habitat"],
        "acquired_at": row["acquired_at"].isoformat() if hasattr(row["acquired_at"], "isoformat") else str(row["acquired_at"]),
        "dies_at": row["dies_at"].isoformat() if row.get("dies_at") and hasattr(row["dies_at"], "isoformat") else (str(row["dies_at"]) if row.get("dies_at") else None),
        "locality_id": row.get("locality_id"),
        "can_breed": row.get("last_bred_date") != datetime.now(timezone.utc).date(),
        "income": pack_animal_income(row, habitat_bonus),
        "habitat_bonus": habitat_bonus > 1.0,
    }


def animal_combat_power(animal: dict) -> int:
    return COMBAT_TIERS[animal["size_trait"]] * 3 + COMBAT_TIERS[animal["survival"]] * 2 + COMBAT_TIERS[animal["appearance"]]


def roll_trait_weighted(chances: list[float]) -> str:
    roll = random.random()
    if roll < chances[0]:
        return "low"
    if roll < chances[0] + chances[1]:
        return "medium"
    return "high"


def resolve_expedition(cur, expedition_id: int, habitat: str, user_id: int) -> dict:
    cur.execute(
        f"SELECT pa.* FROM {ZOOPARK_PACK_ANIMALS_TABLE} pa JOIN {ZOOPARK_EXPEDITION_ANIMALS_TABLE} ea ON ea.animal_id = pa.id WHERE ea.expedition_id=%s",
        (expedition_id,),
    )
    squad = cur.fetchall()
    squad_power = sum(animal_combat_power(animal) for animal in squad)

    chances = EXPEDITION_PARAMS[habitat]["chances"]
    wild = {
        "survival": roll_trait_weighted(chances),
        "reproduction": roll_trait_weighted(chances),
        "appearance": roll_trait_weighted(chances),
        "size_trait": roll_trait_weighted(chances),
        "habitat": habitat,
    }
    wild_power = animal_combat_power(wild)
    result: dict[str, object] = {"squad_power": squad_power, "wild_power": wild_power, "wild": wild}

    if squad_power >= wild_power:
        dies_at = datetime.now(timezone.utc) + timedelta(days=PACK_SURVIVAL_DAYS[wild["survival"]])
        cur.execute(
            f"INSERT INTO {ZOOPARK_PACK_ANIMALS_TABLE} (user_id, survival, reproduction, appearance, size_trait, habitat, dies_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (user_id, wild["survival"], wild["reproduction"], wild["appearance"], wild["size_trait"], wild["habitat"], dies_at),
        )
        result["outcome"] = "victory"
        result["reward_animal_id"] = cur.lastrowid
    else:
        alive_squad = [animal for animal in squad if animal["is_alive"]]
        killed_id = None
        if alive_squad:
            victim = random.choice(alive_squad)
            cur.execute(f"UPDATE {ZOOPARK_PACK_ANIMALS_TABLE} SET is_alive=0 WHERE id=%s", (victim["id"],))
            killed_id = victim["id"]
        result["outcome"] = "defeat"
        result["killed_id"] = killed_id

    cur.execute(f"UPDATE {ZOOPARK_PACK_ANIMALS_TABLE} SET in_expedition=NULL WHERE in_expedition=%s", (expedition_id,))
    cur.execute(f"UPDATE {ZOOPARK_EXPEDITIONS_TABLE} SET status='finished', result_json=%s WHERE id=%s", (json.dumps(result), expedition_id))
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
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            packs_today, _ = get_pack_state(cur, user["id"])
            expire_dead_pack_animals(cur, user["id"])
            cur.execute(
                f"SELECT * FROM {ZOOPARK_PACK_ANIMALS_TABLE} WHERE user_id=%s AND is_alive=1 AND in_expedition IS NULL ORDER BY acquired_at DESC",
                (user["id"],),
            )
            animals = [format_pack_animal(row) for row in cur.fetchall()]

        return {
            "packs_today": packs_today,
            "free_available": packs_today == 0,
            "next_price": pack_next_price(packs_today),
            "animals": animals,
        }
    finally:
        db.close()


def api_packs_open(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)

            rub = int(user["rub"])
            packs_today, date_is_today = get_pack_state(cur, user["id"])
            price = pack_next_price(packs_today)
            if price > 0 and rub < price:
                raise HTTPException(400, f"Недостаточно ₽ (нужно {price})")

            if price > 0:
                cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (rub - price, user["id"]))

            props = roll_pack_animal()
            dies_at = datetime.now(timezone.utc) + timedelta(days=PACK_SURVIVAL_DAYS[props["survival"]])
            cur.execute(
                f"INSERT INTO {ZOOPARK_PACK_ANIMALS_TABLE} (user_id, survival, reproduction, appearance, size_trait, habitat, dies_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (user["id"], props["survival"], props["reproduction"], props["appearance"], props["size_trait"], props["habitat"], dies_at),
            )
            animal_id = cur.lastrowid

            today_str = datetime.now(timezone.utc).date().isoformat()
            new_count = (packs_today + 1) if date_is_today else 1
            cur.execute(
                f"INSERT INTO {ZOOPARK_EXTRA_TABLE} (user_id, packs_today, packs_today_date) VALUES (%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE packs_today=%s, packs_today_date=%s",
                (user["id"], new_count, today_str, new_count, today_str),
            )
        db.commit()
        return {
            "ok": True,
            "price_paid": price,
            "new_rub": rub - price,
            "packs_today": new_count,
            "next_price": pack_next_price(new_count),
            "animal": {
                "id": animal_id,
                **props,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "dies_at": dies_at.isoformat(),
                "locality_id": None,
                "can_breed": True,
                "income": pack_animal_income(props),
            },
        }
    finally:
        db.close()


def api_get_localities(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            ensure_first_locality(cur, user["id"])
            cur.execute(f"SELECT * FROM {ZOOPARK_LOCALITIES_TABLE} WHERE user_id=%s ORDER BY created_at", (user["id"],))
            localities_raw = cur.fetchall()
            expire_dead_pack_animals(cur, user["id"])
            cur.execute(
                f"SELECT * FROM {ZOOPARK_PACK_ANIMALS_TABLE} WHERE user_id=%s AND is_alive=1 AND in_expedition IS NULL ORDER BY acquired_at DESC",
                (user["id"],),
            )
            animals_raw = cur.fetchall()

        db.commit()

        buckets: dict[int | None, list[dict]] = {locality["id"]: [] for locality in localities_raw}
        buckets[None] = []
        for animal in animals_raw:
            locality_id = animal.get("locality_id")
            bucket_key = locality_id if locality_id in buckets else None
            buckets[bucket_key].append(animal)

        return {
            "localities": [
                {
                    "id": locality["id"],
                    "habitat": locality["habitat"],
                    "animals": [format_pack_animal(animal, locality["habitat"]) for animal in buckets[locality["id"]]],
                }
                for locality in localities_raw
            ],
            "unassigned": [format_pack_animal(animal) for animal in buckets[None]],
            "next_price": locality_next_price(len(localities_raw)) if len(localities_raw) < 5 else None,
            "habitats_taken": [locality["habitat"] for locality in localities_raw],
        }
    finally:
        db.close()


def api_buy_locality(
    tg_id: int,
    body: BuyLocalityBody,
):
    if body.habitat not in HABITATS:
        raise HTTPException(400, "Неверная среда обитания")

    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)

            rub = int(user["rub"])
            cur.execute(
                f"SELECT COUNT(*) AS cnt, GROUP_CONCAT(habitat) AS taken FROM {ZOOPARK_LOCALITIES_TABLE} WHERE user_id=%s",
                (user["id"],),
            )
            row = cur.fetchone()
            count = int(row["cnt"] or 0)
            taken = row["taken"].split(",") if row["taken"] else []

            if count >= 5:
                raise HTTPException(400, "Достигнут максимум местностей (5)")
            if body.habitat in taken:
                raise HTTPException(400, "Эта местность уже открыта")

            price = locality_next_price(count)
            if price > 0 and rub < price:
                raise HTTPException(400, f"Недостаточно ₽ (нужно {price:,})")

            if price > 0:
                cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (rub - price, user["id"]))

            cur.execute(f"INSERT INTO {ZOOPARK_LOCALITIES_TABLE} (user_id, habitat) VALUES (%s,%s)", (user["id"], body.habitat))
            locality_id = cur.lastrowid
        db.commit()
        return {"ok": True, "id": locality_id, "habitat": body.habitat, "price_paid": price, "new_rub": rub - price}
    finally:
        db.close()


def api_assign_locality(
    tg_id: int,
    body: AssignLocalityBody,
):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            cur.execute(
                f"SELECT id FROM {ZOOPARK_PACK_ANIMALS_TABLE} WHERE id=%s AND user_id=%s AND is_alive=1",
                (body.animal_id, user["id"]),
            )
            if not cur.fetchone():
                raise HTTPException(404, "Животное не найдено")

            if body.locality_id is not None:
                cur.execute(f"SELECT id FROM {ZOOPARK_LOCALITIES_TABLE} WHERE id=%s AND user_id=%s", (body.locality_id, user["id"]))
                if not cur.fetchone():
                    raise HTTPException(404, "Местность не найдена")

            cur.execute(f"UPDATE {ZOOPARK_PACK_ANIMALS_TABLE} SET locality_id=%s WHERE id=%s", (body.locality_id, body.animal_id))
        db.commit()
        return {"ok": True}
    finally:
        db.close()


def api_breed(
    tg_id: int,
    body: BreedBody,
):
    if body.animal_id_1 == body.animal_id_2:
        raise HTTPException(400, "Нельзя скрещивать животное с самим собой")

    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            today = datetime.now(timezone.utc).date()
            cur.execute(
                f"SELECT * FROM {ZOOPARK_PACK_ANIMALS_TABLE} WHERE id IN (%s,%s) AND user_id=%s AND is_alive=1",
                (body.animal_id_1, body.animal_id_2, user["id"]),
            )
            rows = {row["id"]: row for row in cur.fetchall()}
            if len(rows) != 2:
                raise HTTPException(404, "Одно или оба животных не найдены")

            parent1 = rows[body.animal_id_1]
            parent2 = rows[body.animal_id_2]
            for parent in (parent1, parent2):
                if parent.get("last_bred_date") == today:
                    raise HTTPException(400, "Одно из животных уже скрещивалось сегодня")

            rate = BREED_RATES.get((parent1["reproduction"], parent2["reproduction"]), BREED_RATES.get((parent2["reproduction"], parent1["reproduction"]), 0.60))
            success = random.random() < rate
            cur.execute(f"UPDATE {ZOOPARK_PACK_ANIMALS_TABLE} SET last_bred_date=%s WHERE id IN (%s,%s)", (today, body.animal_id_1, body.animal_id_2))

            offspring = None
            if success:
                props = {
                    "survival": breed_trait(parent1["survival"], parent2["survival"]),
                    "reproduction": breed_trait(parent1["reproduction"], parent2["reproduction"]),
                    "appearance": breed_trait(parent1["appearance"], parent2["appearance"]),
                    "size_trait": breed_trait(parent1["size_trait"], parent2["size_trait"]),
                    "habitat": random.choice([parent1["habitat"], parent2["habitat"]]),
                }
                dies_at = datetime.now(timezone.utc) + timedelta(days=PACK_SURVIVAL_DAYS[props["survival"]])
                cur.execute(
                    f"INSERT INTO {ZOOPARK_PACK_ANIMALS_TABLE} (user_id, survival, reproduction, appearance, size_trait, habitat, dies_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (user["id"], props["survival"], props["reproduction"], props["appearance"], props["size_trait"], props["habitat"], dies_at),
                )
                offspring = {
                    "id": cur.lastrowid,
                    **props,
                    "acquired_at": datetime.now(timezone.utc).isoformat(),
                    "dies_at": dies_at.isoformat(),
                    "locality_id": None,
                    "can_breed": False,
                    "habitat_bonus": False,
                    "income": pack_animal_income(props),
                }
        db.commit()
        return {"ok": True, "success": success, "rate": rate, "animal": offspring}
    finally:
        db.close()


def api_get_expeditions(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            cur.execute(f"SELECT id, habitat FROM {ZOOPARK_LOCALITIES_TABLE} WHERE user_id=%s ORDER BY created_at", (user["id"],))
            localities = [{"id": locality["id"], "habitat": locality["habitat"]} for locality in cur.fetchall()]

            cur.execute(
                f"SELECT * FROM {ZOOPARK_EXPEDITIONS_TABLE} WHERE user_id=%s AND (status='active' OR (status='finished' AND result_seen=0)) ORDER BY started_at DESC LIMIT 1",
                (user["id"],),
            )
            expedition = cur.fetchone()
            active = None

            if expedition:
                expedition_id = expedition["id"]
                if expedition["status"] == "active":
                    ends_at = expedition["ends_at"]
                    if hasattr(ends_at, "tzinfo") and ends_at.tzinfo is None:
                        ends_at = ends_at.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) >= ends_at:
                        result = resolve_expedition(cur, expedition_id, expedition["locality_habitat"], user["id"])
                        db.commit()
                        expedition = {**expedition, "status": "finished", "result_json": json.dumps(result)}

                cur.execute(
                    f"SELECT pa.* FROM {ZOOPARK_PACK_ANIMALS_TABLE} pa JOIN {ZOOPARK_EXPEDITION_ANIMALS_TABLE} ea ON ea.animal_id = pa.id WHERE ea.expedition_id=%s",
                    (expedition_id,),
                )
                squad = [format_pack_animal(animal) for animal in cur.fetchall()]

                result_data = None
                if expedition["status"] == "finished" and expedition.get("result_json"):
                    result_data = json.loads(expedition["result_json"])
                    if result_data.get("outcome") == "victory" and result_data.get("reward_animal_id"):
                        cur.execute(f"SELECT * FROM {ZOOPARK_PACK_ANIMALS_TABLE} WHERE id=%s", (result_data["reward_animal_id"],))
                        reward = cur.fetchone()
                        if reward:
                            result_data["captured_animal"] = format_pack_animal(reward)

                active = {
                    "id": expedition_id,
                    "habitat": expedition["locality_habitat"],
                    "started_at": format_expedition_dt(expedition["started_at"]),
                    "ends_at": format_expedition_dt(expedition["ends_at"]),
                    "status": expedition["status"],
                    "animals": squad,
                    "result": result_data,
                }

            expire_dead_pack_animals(cur, user["id"])
            cur.execute(
                f"SELECT * FROM {ZOOPARK_PACK_ANIMALS_TABLE} WHERE user_id=%s AND is_alive=1 AND in_expedition IS NULL ORDER BY acquired_at DESC",
                (user["id"],),
            )
            available_animals = [format_pack_animal(animal) for animal in cur.fetchall()]
        db.commit()
        return {
            "active": active,
            "localities": localities,
            "available_animals": available_animals,
            "expedition_minutes": {habitat: params["minutes"] for habitat, params in EXPEDITION_PARAMS.items()},
        }
    finally:
        db.close()


def api_start_expedition(
    tg_id: int,
    body: StartExpeditionBody,
):
    if not (3 <= len(body.animal_ids) <= 5):
        raise HTTPException(400, "Отряд: 3–5 животных")

    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            cur.execute(
                f"SELECT id FROM {ZOOPARK_EXPEDITIONS_TABLE} WHERE user_id=%s AND (status='active' OR (status='finished' AND result_seen=0))",
                (user["id"],),
            )
            if cur.fetchone():
                raise HTTPException(400, "Уже есть активная или незавершённая экспедиция")

            cur.execute(f"SELECT habitat FROM {ZOOPARK_LOCALITIES_TABLE} WHERE id=%s AND user_id=%s", (body.locality_id, user["id"]))
            locality = cur.fetchone()
            if not locality:
                raise HTTPException(404, "Местность не найдена")

            placeholders = ",".join(["%s"] * len(body.animal_ids))
            cur.execute(
                f"SELECT * FROM {ZOOPARK_PACK_ANIMALS_TABLE} WHERE id IN ({placeholders}) AND user_id=%s AND is_alive=1 AND in_expedition IS NULL",
                (*body.animal_ids, user["id"]),
            )
            valid_animals = cur.fetchall()
            if len(valid_animals) != len(body.animal_ids):
                raise HTTPException(400, "Некоторые животные недоступны")

            now = datetime.now(timezone.utc)
            ends_at = now + timedelta(minutes=EXPEDITION_PARAMS[locality["habitat"]]["minutes"])
            cur.execute(
                f"INSERT INTO {ZOOPARK_EXPEDITIONS_TABLE} (user_id, locality_habitat, ends_at) VALUES (%s,%s,%s)",
                (user["id"], locality["habitat"], ends_at),
            )
            expedition_id = cur.lastrowid
            for animal_id in body.animal_ids:
                cur.execute(f"INSERT INTO {ZOOPARK_EXPEDITION_ANIMALS_TABLE} (expedition_id, animal_id) VALUES (%s,%s)", (expedition_id, animal_id))

            cur.execute(
                f"UPDATE {ZOOPARK_PACK_ANIMALS_TABLE} SET in_expedition=%s WHERE id IN ({placeholders}) AND user_id=%s",
                (expedition_id, *body.animal_ids, user["id"]),
            )
        db.commit()
        return {
            "ok": True,
            "expedition": {
                "id": expedition_id,
                "habitat": locality["habitat"],
                "started_at": format_expedition_dt(now),
                "ends_at": format_expedition_dt(ends_at),
                "status": "active",
                "animals": [format_pack_animal(animal) for animal in valid_animals],
                "result": None,
            },
        }
    finally:
        db.close()


def api_finish_expedition(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            cur.execute(f"SELECT * FROM {ZOOPARK_EXPEDITIONS_TABLE} WHERE user_id=%s AND status='active' ORDER BY started_at DESC LIMIT 1", (user["id"],))
            expedition = cur.fetchone()
            if not expedition:
                raise HTTPException(400, "Нет активной экспедиции")

            ends_at = expedition["ends_at"]
            if hasattr(ends_at, "tzinfo") and ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < ends_at:
                raise HTTPException(400, "Экспедиция ещё не завершена")

            result = resolve_expedition(cur, expedition["id"], expedition["locality_habitat"], user["id"])
        db.commit()

        if result.get("outcome") == "victory" and result.get("reward_animal_id"):
            db2 = get_db()
            try:
                with db2.cursor() as cur2:
                    cur2.execute(f"SELECT * FROM {ZOOPARK_PACK_ANIMALS_TABLE} WHERE id=%s", (result["reward_animal_id"],))
                    reward = cur2.fetchone()
                    if reward:
                        result["captured_animal"] = format_pack_animal(reward)
            finally:
                db2.close()

        return {"ok": True, "result": result}
    finally:
        db.close()


def api_dismiss_expedition(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            cur.execute(
                f"UPDATE {ZOOPARK_EXPEDITIONS_TABLE} SET result_seen=1 WHERE user_id=%s AND status='finished' AND result_seen=0",
                (user["id"],),
            )
        db.commit()
        return {"ok": True}
    finally:
        db.close()
