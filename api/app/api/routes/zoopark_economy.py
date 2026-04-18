from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from api.app.zoopark.catalog import ANIMAL_BY_ID, ANIMAL_STRING_TO_DB, AVIARY_BY_ID, AVIARY_STRING_TO_DB, RUB_PER_USD
from api.app.zoopark.profile import bump_data_version, get_animals, get_aviaries, get_user
from api.app.zoopark.runtime import auth, get_db


router = APIRouter(tags=["zoopark-economy"])


class BuyAnimalBody(BaseModel):
    animal_id: str
    quantity: int = 1


class BuyAviaryBody(BaseModel):
    aviary_id: str


class BankExchangeBody(BaseModel):
    from_: str = Field(alias="from")
    amount: float


@router.post("/api/buy_animal")
def buy_animal(
    body: BuyAnimalBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    tg_id = auth(x_init_data, x_dev_user_id)
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
            cur.execute("UPDATE users SET rub=%s WHERE id=%s", (new_rub, uid))
            cur.execute("SELECT id, quantity FROM animals WHERE user_id=%s AND animal_info_id=%s", (uid, db_id))
            existing = cur.fetchone()
            if existing:
                new_qty = int(existing["quantity"]) + qty
                cur.execute("UPDATE animals SET quantity=%s WHERE user_id=%s AND animal_info_id=%s", (new_qty, uid, db_id))
            else:
                new_qty = qty
                cur.execute(
                    "INSERT INTO animals (user_id, animal_info_id, quantity, income, price) VALUES (%s,%s,%s,%s,%s)",
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


@router.post("/api/buy_aviary")
def buy_aviary(
    body: BuyAviaryBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    tg_id = auth(x_init_data, x_dev_user_id)
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
            uid = user["id"]
            if int(user["rub"]) < aviary_def["price"]:
                raise HTTPException(400, "Недостаточно рублей")

            new_rub = int(user["rub"]) - aviary_def["price"]
            cur.execute("UPDATE users SET rub=%s WHERE id=%s", (new_rub, uid))
            cur.execute("SELECT id, quantity FROM aviaries WHERE user_id=%s AND aviary_info_id=%s", (uid, db_id))
            existing = cur.fetchone()
            if existing:
                new_count = int(existing["quantity"]) + 1
                cur.execute(
                    "UPDATE aviaries SET quantity=%s, buy_count=buy_count+1 WHERE user_id=%s AND aviary_info_id=%s",
                    (new_count, uid, db_id),
                )
            else:
                new_count = 1
                cur.execute(
                    "INSERT INTO aviaries (user_id, aviary_info_id, price, size, quantity, buy_count) VALUES (%s,%s,%s,%s,1,1)",
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


@router.get("/api/bank")
def bank(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    auth(x_init_data, x_dev_user_id)
    return {
        "rub_rate": RUB_PER_USD,
        "usd_rate": 1 / RUB_PER_USD,
        "rub_discount": 0,
        "usd_discount": 0,
        "min_exchange_rub": RUB_PER_USD,
        "min_exchange_usd": 1,
    }


@router.post("/api/bank/exchange")
def bank_exchange(
    body: BankExchangeBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    tg_id = auth(x_init_data, x_dev_user_id)
    amount = float(body.amount)
    if amount <= 0:
        raise HTTPException(400, "Сумма должна быть > 0")

    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
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

            cur.execute("UPDATE users SET rub=%s, usd=%s WHERE id=%s", (new_rub, new_usd, uid))
        db.commit()
        return {"ok": True, "new_rub": new_rub, "new_usd": new_usd}
    finally:
        db.close()
