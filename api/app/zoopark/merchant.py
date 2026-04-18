from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from api.app.zoopark.catalog import ANIMALS, ANIMAL_BY_DB_ID, ANIMAL_BY_ID, ANIMAL_STRING_TO_DB, AVIARY_BY_ID
from api.app.zoopark.profile import bump_data_version, get_animals, get_aviaries, get_user
from api.app.zoopark.runtime import get_db


def ensure_merchant(cur, user_id: int, animals: list[dict]) -> list[dict]:
    cur.execute("SELECT * FROM merchants WHERE user_id=%s", (user_id,))
    existing = cur.fetchall()
    if existing:
        return existing

    owned = [ANIMAL_BY_ID[animal["animal_id"]] for animal in animals if animal["animal_id"] in ANIMAL_BY_ID]
    pool = owned if owned else ANIMALS[:10]
    picks = random.sample(pool, min(3, len(pool)))

    cur.execute("DELETE FROM merchants WHERE user_id=%s", (user_id,))
    for pick in picks:
        discount = random.choice([5, 10, 15, 20, 25, 30])
        discounted = int(pick["price"] * (1 - discount / 100))
        quantity = random.randint(1, 3)
        cur.execute(
            "INSERT INTO merchants (user_id, animal_info_id, name, discount, price_with_discount, quantity_animals, price, first_offer_bought) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,0)",
            (user_id, ANIMAL_STRING_TO_DB[pick["id"]], pick["name"], discount, discounted, quantity, pick["price"]),
        )

    cur.execute("SELECT * FROM merchants WHERE user_id=%s", (user_id,))
    return cur.fetchall()


def do_merchant_buy(tg_id: int, slot: int) -> dict:
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            user_id = user["id"]
            animals = get_animals(cur, user_id)
            offers = ensure_merchant(cur, user_id, animals)
            if slot < 1 or slot > len(offers):
                raise HTTPException(400, "Неверный слот")

            offer = offers[slot - 1]
            if offer.get("first_offer_bought"):
                raise HTTPException(400, "Уже куплено")

            animal_def = ANIMAL_BY_DB_ID.get(int(offer["animal_info_id"]))
            if not animal_def:
                raise HTTPException(400, "Животное не найдено")

            quantity = int(offer["quantity_animals"] or 1)
            cost = int(offer["price_with_discount"] or animal_def["price"]) * quantity
            if int(user["rub"]) < cost:
                raise HTTPException(400, "Недостаточно рублей")

            aviaries = get_aviaries(cur, user_id)
            total_seats = sum(AVIARY_BY_ID[aviary["aviary_id"]]["seats"] * aviary["count"] for aviary in aviaries)
            occupied = sum(animal["quantity"] for animal in animals)
            if total_seats - occupied < quantity:
                raise HTTPException(400, "Нет мест")

            new_rub = int(user["rub"]) - cost
            cur.execute("UPDATE users SET rub=%s WHERE id=%s", (new_rub, user_id))
            cur.execute(
                "UPDATE merchants SET first_offer_bought=1 WHERE user_id=%s AND animal_info_id=%s",
                (user_id, offer["animal_info_id"]),
            )

            db_id = ANIMAL_STRING_TO_DB[animal_def["id"]]
            cur.execute("SELECT id, quantity FROM animals WHERE user_id=%s AND animal_info_id=%s", (user_id, db_id))
            existing = cur.fetchone()
            if existing:
                new_quantity = int(existing["quantity"]) + quantity
                cur.execute(
                    "UPDATE animals SET quantity=%s WHERE user_id=%s AND animal_info_id=%s",
                    (new_quantity, user_id, db_id),
                )
            else:
                new_quantity = quantity
                cur.execute(
                    "INSERT INTO animals (user_id, animal_info_id, quantity, income, price) VALUES (%s,%s,%s,%s,%s)",
                    (user_id, db_id, quantity, animal_def["income"], animal_def["price"]),
                )

            bump_data_version(cur, user_id)
        db.commit()
        return {"ok": True, "new_rub": new_rub, "new_quantity": new_quantity}
    finally:
        db.close()


def get_merchant_animals(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            offers = ensure_merchant(cur, user["id"], get_animals(cur, user["id"]))
        db.commit()

        animals: list[dict] = []
        for index, offer in enumerate(offers[:3]):
            animal_def = ANIMAL_BY_DB_ID.get(int(offer["animal_info_id"]))
            if not animal_def:
                continue

            animals.append(
                {
                    "slot": index + 1,
                    "animal_id": animal_def["id"],
                    "quantity": int(offer["quantity_animals"] or 1),
                    "original_price": int(offer["price"] or animal_def["price"]),
                    "discount_pct": int(offer["discount"] or 0),
                    "final_price": int(offer["price_with_discount"] or animal_def["price"]),
                }
            )

        return {
            "animals": animals,
            "refreshes_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        }
    finally:
        db.close()


def buy_merchant_offer(tg_id: int, slot: int):
    return do_merchant_buy(tg_id, slot)
