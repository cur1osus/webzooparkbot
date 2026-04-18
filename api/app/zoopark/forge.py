from __future__ import annotations

import json
import random

from fastapi import HTTPException
from pydantic import BaseModel

from api.app.zoopark.profile import get_forge_items, get_user
from api.app.zoopark.runtime import get_db


FORGE_TYPES: dict[str, dict] = {
    "income_boost": {"name": "Зелье дохода", "emoji": "💰", "cost": 5, "base_effect": 0.05},
    "aviary_sale": {"name": "Скидка на вольер", "emoji": "🏗", "cost": 3, "base_effect": 0.10},
    "bank_bonus": {"name": "Банковский бонус", "emoji": "🏦", "cost": 8, "base_effect": 0.08},
    "extra_moves": {"name": "Доп. ходы", "emoji": "🎮", "cost": 4, "base_effect": 1.0},
}
FORGE_RARITIES = ["common", "rare", "epic", "mythic"]
FORGE_WEIGHTS = [0.4, 0.3, 0.2, 0.1]
RARITY_MULT = {"common": 1.0, "rare": 1.5, "epic": 2.5, "mythic": 4.0}
RARITY_SV = {"common": 1, "rare": 3, "epic": 9, "mythic": 27}


class ForgeCreateBody(BaseModel):
    item_type: str


class ForgeItemIdBody(BaseModel):
    item_id: str


class ForgeActivateBody(BaseModel):
    set_id: str


class ForgeMergeBody(BaseModel):
    item_id1: str
    item_id2: str


def make_forge_item(item_type: str, rarity: str | None = None) -> dict:
    if item_type not in FORGE_TYPES:
        item_type = random.choice(list(FORGE_TYPES.keys()))
    if rarity is None:
        rarity = random.choices(FORGE_RARITIES, FORGE_WEIGHTS)[0]

    template = FORGE_TYPES[item_type]
    effect = round(template["base_effect"] * RARITY_MULT.get(rarity, 1), 3)
    labels = {
        "income_boost": f"Доход +{int(effect * 100)}%",
        "aviary_sale": f"Вольеры -{int(effect * 100)}%",
        "bank_bonus": f"Банк +{int(effect * 100)}%",
        "extra_moves": f"+{int(effect)} ход",
    }
    return {
        "item_type": item_type,
        "name": template["name"],
        "emoji": template["emoji"],
        "rarity": rarity,
        "effect_value": effect,
        "effect_label": labels.get(item_type, ""),
        "sv": RARITY_SV.get(rarity, 1),
    }


def api_forge_items(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            return {"items": get_forge_items(cur, user["id"])}
    finally:
        db.close()


def api_forge_create(
    tg_id: int,
    body: ForgeCreateBody,
):
    cost = FORGE_TYPES.get(body.item_type, {}).get("cost", 5)
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            user_id = user["id"]
            paw_coins = int(user["paw_coins"])
            if paw_coins < cost:
                raise HTTPException(400, f"Нужно {cost} 🐾")

            new_paw_coins = paw_coins - cost
            item = make_forge_item(body.item_type)
            properties = json.dumps(
                {
                    "item_type": item["item_type"],
                    "effect_label": item["effect_label"],
                    "effect_value": item["effect_value"],
                    "sv": item["sv"],
                }
            )
            cur.execute(
                "INSERT INTO items (user_id, emoji, name, lvl, properties, rarity, is_active) VALUES (%s,%s,%s,1,%s,%s,0)",
                (user_id, item["emoji"], item["name"], properties, item["rarity"]),
            )
            item_id = cur.lastrowid
            cur.execute("UPDATE users SET paw_coins=%s WHERE id=%s", (new_paw_coins, user_id))
        db.commit()
        return {
            "ok": True,
            "item": {
                "id": str(item_id),
                "item_type": item["item_type"],
                "name": item["name"],
                "icon": item["emoji"],
                "rarity": item["rarity"],
                "level": 1,
                "effect_label": item["effect_label"],
                "effect_value": item["effect_value"],
                "sv": item["sv"],
                "is_active": False,
            },
            "cost_paw_coins": cost,
            "new_paw_coins": new_paw_coins,
        }
    finally:
        db.close()


def api_forge_upgrade(
    tg_id: int,
    body: ForgeItemIdBody,
):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            user_id = user["id"]
            try:
                item_id = int(body.item_id)
            except ValueError as exc:
                raise HTTPException(400, "Неверный ID") from exc

            cur.execute("SELECT * FROM items WHERE id=%s AND user_id=%s", (item_id, user_id))
            item = cur.fetchone()
            if not item:
                raise HTTPException(404, "Предмет не найден")

            cost = int(item["lvl"]) * 3
            paw_coins = int(user["paw_coins"])
            if paw_coins < cost:
                raise HTTPException(400, f"Нужно {cost} 🐾")

            new_paw_coins = paw_coins - cost
            new_level = int(item["lvl"]) + 1
            properties = json.loads(item["properties"]) if item["properties"] else {}
            properties["effect_value"] = round(float(properties.get("effect_value", 0)) * 1.2, 3)
            cur.execute(
                "UPDATE items SET lvl=%s, properties=%s WHERE id=%s",
                (new_level, json.dumps(properties), item_id),
            )
            cur.execute("UPDATE users SET paw_coins=%s WHERE id=%s", (new_paw_coins, user_id))
        db.commit()
        return {
            "ok": True,
            "item": {
                "id": str(item_id),
                "item_type": properties.get("item_type", ""),
                "name": item["name"],
                "icon": item["emoji"],
                "rarity": item["rarity"],
                "level": new_level,
                "effect_label": properties.get("effect_label", ""),
                "effect_value": properties.get("effect_value", 0),
                "sv": properties.get("sv", 0),
                "is_active": bool(item["is_active"]),
            },
            "cost": cost,
            "new_paw_coins": new_paw_coins,
        }
    finally:
        db.close()


def api_forge_merge(
    tg_id: int,
    body: ForgeMergeBody,
):
    cost = 15
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            user_id = user["id"]
            try:
                item_id1 = int(body.item_id1)
                item_id2 = int(body.item_id2)
            except ValueError as exc:
                raise HTTPException(400, "Неверный ID") from exc

            if item_id1 == item_id2:
                raise HTTPException(400, "Нельзя объединить предмет сам с собой")

            cur.execute("SELECT * FROM items WHERE id IN (%s,%s) AND user_id=%s", (item_id1, item_id2, user_id))
            items = cur.fetchall()
            if len(items) < 2:
                raise HTTPException(404, "Предметы не найдены")

            paw_coins = int(user["paw_coins"])
            if paw_coins < cost:
                raise HTTPException(400, f"Нужно {cost} 🐾")

            new_paw_coins = paw_coins - cost
            for item in items:
                cur.execute("DELETE FROM items WHERE id=%s", (item["id"],))

            properties = json.loads(items[0]["properties"]) if items[0]["properties"] else {}
            old_rarity = items[0]["rarity"]
            new_rarity = {"common": "rare", "rare": "epic", "epic": "mythic", "mythic": "mythic"}.get(old_rarity, "rare")
            item = make_forge_item(properties.get("item_type", "income_boost"), new_rarity)
            new_properties = json.dumps(
                {
                    "item_type": item["item_type"],
                    "effect_label": item["effect_label"],
                    "effect_value": item["effect_value"],
                    "sv": item["sv"],
                }
            )
            cur.execute(
                "INSERT INTO items (user_id, emoji, name, lvl, properties, rarity, is_active) VALUES (%s,%s,%s,1,%s,%s,0)",
                (user_id, item["emoji"], item["name"], new_properties, item["rarity"]),
            )
            new_item_id = cur.lastrowid
            cur.execute("UPDATE users SET paw_coins=%s WHERE id=%s", (new_paw_coins, user_id))
        db.commit()
        return {
            "ok": True,
            "new_item": {
                "id": str(new_item_id),
                "item_type": item["item_type"],
                "name": item["name"],
                "icon": item["emoji"],
                "rarity": item["rarity"],
                "level": 1,
                "effect_label": item["effect_label"],
                "effect_value": item["effect_value"],
                "sv": item["sv"],
                "is_active": False,
            },
            "cost_paw_coins": cost,
            "new_paw_coins": new_paw_coins,
        }
    finally:
        db.close()


def api_forge_activate(
    tg_id: int,
    body: ForgeActivateBody,
):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            try:
                item_id = int(body.set_id)
            except ValueError as exc:
                raise HTTPException(400, "Неверный ID") from exc

            cur.execute("SELECT id, is_active FROM items WHERE id=%s AND user_id=%s", (item_id, user["id"]))
            item = cur.fetchone()
            if not item:
                raise HTTPException(404, "Предмет не найден")

            cur.execute("UPDATE items SET is_active=%s WHERE id=%s", (0 if item["is_active"] else 1, item_id))
        db.commit()
        return {"ok": True}
    finally:
        db.close()
