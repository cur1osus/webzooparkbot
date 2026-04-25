from __future__ import annotations

from fastapi import HTTPException

from api.app.db.connection import get_db
from api.app.db.tables import ZOOPARK_ANIMALS_TABLE, ZOOPARK_AVIARIES_TABLE, ZOOPARK_USERS_TABLE
from api.app.schemas.economy import BankExchangeBody, BuyAnimalBody, BuyAviaryBody
from api.app.zoopark.catalog import ANIMAL_BY_ID, ANIMAL_STRING_TO_DB, AVIARY_BY_ID, AVIARY_STRING_TO_DB, RUB_PER_USD
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import bump_data_version, get_animals, get_aviaries, get_user


def buy_animal(tg_id: int, body: BuyAnimalBody) -> dict:
    animal_def = ANIMAL_BY_ID.get(body.animal_id)
    if animal_def is None:
        raise HTTPException(400, "Неизвестное животное")

    qty = max(1, body.quantity)
    db_id = ANIMAL_STRING_TO_DB[body.animal_id]
    cost = animal_def["price"] * qty

    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)
            uid = user["id"]
            if int(user["rub"]) < cost:
                raise HTTPException(400, "Недостаточно рублей")

            animals = get_animals(cur, uid)
            aviaries = get_aviaries(cur, uid)
            total_seats = sum(AVIARY_BY_ID[aviary["aviary_id"]]["seats"] * aviary["count"] for aviary in aviaries)
            occupied = sum(animal["quantity"] for animal in animals)
            if total_seats - occupied < qty:
                raise HTTPException(400, f"Нет мест в вольерах (нужно {qty}, свободно {total_seats - occupied})")

            new_rub = int(user["rub"]) - cost
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (new_rub, uid))
            cur.execute(f"SELECT id, quantity FROM {ZOOPARK_ANIMALS_TABLE} WHERE user_id=%s AND animal_info_id=%s", (uid, db_id))
            existing = cur.fetchone()
            if existing:
                new_qty = int(existing["quantity"]) + qty
                cur.execute(f"UPDATE {ZOOPARK_ANIMALS_TABLE} SET quantity=%s WHERE user_id=%s AND animal_info_id=%s", (new_qty, uid, db_id))
            else:
                new_qty = qty
                cur.execute(
                    f"INSERT INTO {ZOOPARK_ANIMALS_TABLE} (user_id, animal_info_id, quantity, income, price) VALUES (%s,%s,%s,%s,%s)",
                    (uid, db_id, qty, animal_def["income"], animal_def["price"]),
                )
            bump_data_version(cur, uid)
        db.commit()
        return {
            "ok": True,
            "new_rub": new_rub,
            "new_quantity": new_qty,
            "new_total_animals": occupied + qty,
            "new_free_seats": total_seats - occupied - qty,
        }
    finally:
        db.close()


def buy_aviary(tg_id: int, body: BuyAviaryBody) -> dict:
    aviary_def = AVIARY_BY_ID.get(body.aviary_id)
    if aviary_def is None:
        raise HTTPException(400, "Неизвестный вольер")

    db_id = AVIARY_STRING_TO_DB[body.aviary_id]
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)
            uid = user["id"]
            if int(user["rub"]) < aviary_def["price"]:
                raise HTTPException(400, "Недостаточно рублей")

            new_rub = int(user["rub"]) - aviary_def["price"]
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (new_rub, uid))
            cur.execute(f"SELECT id, quantity FROM {ZOOPARK_AVIARIES_TABLE} WHERE user_id=%s AND aviary_info_id=%s", (uid, db_id))
            existing = cur.fetchone()
            if existing:
                new_count = int(existing["quantity"]) + 1
                cur.execute(
                    f"UPDATE {ZOOPARK_AVIARIES_TABLE} SET quantity=%s, buy_count=buy_count+1 WHERE user_id=%s AND aviary_info_id=%s",
                    (new_count, uid, db_id),
                )
            else:
                new_count = 1
                cur.execute(
                    f"INSERT INTO {ZOOPARK_AVIARIES_TABLE} (user_id, aviary_info_id, price, size, quantity, buy_count) VALUES (%s,%s,%s,%s,1,1)",
                    (uid, db_id, aviary_def["price"], aviary_def["seats"]),
                )

            aviaries = get_aviaries(cur, uid)
            animals = get_animals(cur, uid)
            total_seats = sum(AVIARY_BY_ID[aviary["aviary_id"]]["seats"] * aviary["count"] for aviary in aviaries)
            occupied = sum(animal["quantity"] for animal in animals)
            bump_data_version(cur, uid)
        db.commit()
        return {
            "ok": True,
            "new_rub": new_rub,
            "new_count": new_count,
            "new_total_seats": total_seats,
            "new_free_seats": max(0, total_seats - occupied),
        }
    finally:
        db.close()


def bank() -> dict:
    return {
        "rub_rate": RUB_PER_USD,
        "usd_rate": 1 / RUB_PER_USD,
        "rub_discount": 0,
        "usd_discount": 0,
        "min_exchange_rub": RUB_PER_USD,
        "min_exchange_usd": 1,
    }


def bank_exchange(tg_id: int, body: BankExchangeBody) -> dict:
    amount = float(body.amount)
    if amount <= 0:
        raise HTTPException(400, "Сумма должна быть > 0")

    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            user, _income, _expenses = sync_passive_balance(cur, user)
            uid = user["id"]
            rub = int(user["rub"])
            usd = int(user["usd"])

            if body.from_ == "rub":
                cost = int(amount)
                if rub < cost:
                    raise HTTPException(400, "Недостаточно рублей")
                gain = int(amount / RUB_PER_USD)
                if gain < 1:
                    raise HTTPException(400, f"Минимум {RUB_PER_USD} ₽")
                new_rub, new_usd = rub - cost, usd + gain
            else:
                cost = int(amount)
                if usd < cost:
                    raise HTTPException(400, "Недостаточно долларов")
                new_rub, new_usd = rub + int(amount * RUB_PER_USD), usd - cost

            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s, usd=%s WHERE id=%s", (new_rub, new_usd, uid))
        db.commit()
        return {"ok": True, "new_rub": new_rub, "new_usd": new_usd}
    finally:
        db.close()
