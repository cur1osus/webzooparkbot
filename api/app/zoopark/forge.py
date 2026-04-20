from __future__ import annotations

import json
import random

from fastapi import HTTPException
from pydantic import BaseModel

from api.app.zoopark.catalog import ANIMALS
from api.app.zoopark.db_tables import ZOOPARK_ITEMS_TABLE, ZOOPARK_USERS_TABLE
from api.app.zoopark.profile import get_forge_items, get_user
from api.app.zoopark.runtime import get_db

# ─── Catalog helpers ──────────────────────────────────────────────────────────

ANIMAL_IDS = [a["id"] for a in ANIMALS]
ANIMAL_NAMES: dict[str, str] = {a["id"]: a["name"] for a in ANIMALS}

# ─── Rarity config ────────────────────────────────────────────────────────────

RARITIES = ["common", "rare", "epic", "mythical"]
RARITY_PROBS = [0.50, 0.30, 0.13, 0.07]
RARITY_PROPS_COUNT = {"common": 1, "rare": 2, "epic": 3, "mythical": 4, "legendary": 5}
RARITY_FROM_COUNT: dict[int, str] = {1: "common", 2: "rare", 3: "epic", 4: "mythical", 5: "legendary"}

RARITY_ICONS = {
    "common": "🔩", "rare": "💙", "epic": "💜", "mythical": "🔴", "legendary": "⭐",
}
RARITY_NAMES = {
    "common": "Обычный", "rare": "Редкий", "epic": "Эпический",
    "mythical": "Мифический", "legendary": "Легендарный",
}

# ─── Property config ──────────────────────────────────────────────────────────

PROPERTY_TYPES = [
    "animal_income", "income_boost", "bank_rate",
    "aviary_discount", "animal_discount",
    "extra_turns", "last_chance", "bonus_rerolls",
]
PROPERTY_WEIGHTS = [25, 25, 20, 15, 15, 10, 10, 10]

PROPERTY_RANGES: dict[str, dict[str, tuple[int, int]]] = {
    "animal_income":   {"common": (1, 5),  "rare": (3, 9),   "epic": (9, 14),  "mythical": (10, 20), "legendary": (10, 20)},
    "income_boost":    {"common": (5, 7),  "rare": (10, 20), "epic": (25, 30), "mythical": (30, 45), "legendary": (30, 45)},
    "bank_rate":       {"common": (5, 10), "rare": (10, 20), "epic": (20, 25), "mythical": (23, 30), "legendary": (23, 30)},
    "aviary_discount": {"common": (5, 9),  "rare": (9, 12),  "epic": (10, 20), "mythical": (15, 20), "legendary": (15, 20)},
    "animal_discount": {"common": (3, 10), "rare": (10, 14), "epic": (20, 25), "mythical": (30, 50), "legendary": (30, 50)},
    "extra_turns":     {"common": (1, 1),  "rare": (1, 2),   "epic": (1, 3),   "mythical": (1, 4),   "legendary": (1, 5)},
    "last_chance":     {"common": (5, 10), "rare": (5, 10),  "epic": (5, 10),  "mythical": (5, 10),  "legendary": (5, 10)},
    "bonus_rerolls":   {"common": (1, 1),  "rare": (1, 2),   "epic": (1, 3),   "mythical": (1, 4),   "legendary": (1, 5)},
}

PROPERTY_BASE_LABELS = {
    "animal_income":   "Доход {animal}",
    "income_boost":    "Общий доход",
    "bank_rate":       "Курс банка",
    "aviary_discount": "Скидка на вольеры",
    "animal_discount": "Скидка на животных",
    "extra_turns":     "Доп. ходы",
    "last_chance":     "Последний шанс",
    "bonus_rerolls":   "Перебросы бонуса",
}

# ─── Forge economy ────────────────────────────────────────────────────────────

FORGE_CREATE_BASE_USD = 100_000
FORGE_CREATE_PAW = 350
FORGE_CREATE_MULT = 1.15
FORGE_UPGRADE_BASE_USD = 30_000
FORGE_SELL_USD = 80_000
FORGE_MERGE_BASE_USD = 100_000
MAX_ITEM_LEVEL = 12
MAX_ACTIVE_ITEMS = 3


# ─── Request models ───────────────────────────────────────────────────────────

class ForgeCreateBody(BaseModel):
    currency: str = "usd"  # "usd" | "paw"


class ForgeItemIdBody(BaseModel):
    item_id: str


class ForgeActivateBody(BaseModel):
    set_id: str


class ForgeMergeBody(BaseModel):
    item_id1: str
    item_id2: str


# ─── Property helpers ─────────────────────────────────────────────────────────

def _prop_label(prop_type: str, value: int, animal_id: str | None = None) -> str:
    if prop_type == "animal_income":
        aname = ANIMAL_NAMES.get(animal_id or "", "животного")
        return f"Доход {aname} +{value}%"
    if prop_type in ("income_boost", "last_chance"):
        return f"{PROPERTY_BASE_LABELS[prop_type]} +{value}%"
    if prop_type in ("bank_rate", "aviary_discount", "animal_discount"):
        return f"{PROPERTY_BASE_LABELS[prop_type]} -{value}%"
    return f"{PROPERTY_BASE_LABELS.get(prop_type, prop_type)} +{value}"


def _rebuild_label(prop: dict) -> None:
    prop["label"] = _prop_label(prop["type"], prop["value"], prop.get("animal_id"))


def _make_property(prop_type: str, rarity: str) -> dict:
    lo, hi = PROPERTY_RANGES[prop_type].get(rarity, PROPERTY_RANGES[prop_type]["common"])
    value = random.randint(lo, hi)
    prop: dict = {"type": prop_type, "value": value, "label": _prop_label(prop_type, value)}
    if prop_type == "animal_income":
        animal_id = random.choice(ANIMAL_IDS)
        prop["animal_id"] = animal_id
        prop["label"] = _prop_label(prop_type, value, animal_id)
    return prop


def _make_properties(rarity: str) -> list[dict]:
    count = RARITY_PROPS_COUNT[rarity]
    candidates = list(range(len(PROPERTY_TYPES)))
    chosen_indices: list[int] = []
    for _ in range(count):
        if not candidates:
            break
        idx = random.choices(candidates, [PROPERTY_WEIGHTS[i] for i in candidates])[0]
        chosen_indices.append(idx)
        candidates.remove(idx)
    return [_make_property(PROPERTY_TYPES[i], rarity) for i in chosen_indices]


def _item_dict(item_id: int, emoji: str, name: str, rarity: str, level: int, props: list[dict], is_active: bool) -> dict:
    return {
        "id": str(item_id),
        "name": name,
        "icon": emoji,
        "rarity": rarity,
        "level": level,
        "properties": props,
        "is_active": is_active,
    }


# ─── API handlers ─────────────────────────────────────────────────────────────

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


def api_forge_create(tg_id: int, body: ForgeCreateBody):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            user_id = user["id"]
            cur.execute(f"SELECT COUNT(*) as cnt FROM {ZOOPARK_ITEMS_TABLE} WHERE user_id=%s", (user_id,))
            item_count = int(cur.fetchone()["cnt"])

            usd_cost = int(FORGE_CREATE_BASE_USD * (FORGE_CREATE_MULT ** item_count))
            paw_cost = FORGE_CREATE_PAW
            currency = body.currency if body.currency in ("usd", "paw") else "usd"

            if currency == "paw":
                if int(user["paw_coins"]) < paw_cost:
                    raise HTTPException(400, f"Нужно {paw_cost} PawCoins")
                cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET paw_coins=paw_coins-%s WHERE id=%s", (paw_cost, user_id))
                new_paw = int(user["paw_coins"]) - paw_cost
                new_usd = int(user["usd"])
                cost_usd_out = None
                cost_paw_out: int | None = paw_cost
            else:
                if int(user["usd"]) < usd_cost:
                    raise HTTPException(400, f"Нужно ${usd_cost:,}")
                cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET usd=usd-%s WHERE id=%s", (usd_cost, user_id))
                new_usd = int(user["usd"]) - usd_cost
                new_paw = int(user["paw_coins"])
                cost_usd_out: int | None = usd_cost
                cost_paw_out = None

            rarity = random.choices(RARITIES, RARITY_PROBS)[0]
            props = _make_properties(rarity)
            emoji = RARITY_ICONS[rarity]
            name = f"{RARITY_NAMES[rarity]} артефакт"

            cur.execute(
                f"INSERT INTO {ZOOPARK_ITEMS_TABLE} (user_id, emoji, name, lvl, properties, rarity, is_active) VALUES (%s,%s,%s,0,%s,%s,0)",
                (user_id, emoji, name, json.dumps(props, ensure_ascii=False), rarity),
            )
            item_id = cur.lastrowid
        db.commit()
        return {
            "ok": True,
            "item": _item_dict(item_id, emoji, name, rarity, 0, props, False),
            "cost_usd": cost_usd_out,
            "new_usd": new_usd,
            "cost_paw_coins": cost_paw_out,
            "new_paw_coins": new_paw,
        }
    finally:
        db.close()


def api_forge_upgrade(tg_id: int, body: ForgeItemIdBody):
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

            cur.execute(f"SELECT * FROM {ZOOPARK_ITEMS_TABLE} WHERE id=%s AND user_id=%s", (item_id, user_id))
            item = cur.fetchone()
            if not item:
                raise HTTPException(404, "Предмет не найден")

            level = int(item["lvl"])
            if level >= MAX_ITEM_LEVEL:
                raise HTTPException(400, f"Максимальный уровень {MAX_ITEM_LEVEL}")

            cost_usd = FORGE_UPGRADE_BASE_USD * (level + 1)
            if int(user["usd"]) < cost_usd:
                raise HTTPException(400, f"Нужно ${cost_usd:,}")

            success_pct = max(0, 100 - 8 * level)
            success = random.randint(1, 100) <= success_pct
            new_usd = int(user["usd"]) - cost_usd
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET usd=%s WHERE id=%s", (new_usd, user_id))

            props: list[dict] = json.loads(item["properties"]) if item["properties"] else []
            new_level = level

            if success and props:
                new_level = level + 1
                idx = random.randint(0, len(props) - 1)
                props[idx] = dict(props[idx])
                props[idx]["value"] = props[idx].get("value", 0) + 1
                _rebuild_label(props[idx])
                cur.execute(
                    f"UPDATE {ZOOPARK_ITEMS_TABLE} SET lvl=%s, properties=%s WHERE id=%s",
                    (new_level, json.dumps(props, ensure_ascii=False), item_id),
                )
        db.commit()
        return {
            "ok": True,
            "success": success,
            "success_pct": success_pct,
            "item": _item_dict(item_id, item["emoji"], item["name"], item["rarity"], new_level, props, bool(item["is_active"])),
            "cost_usd": cost_usd,
            "new_usd": new_usd,
        }
    finally:
        db.close()


def api_forge_merge(tg_id: int, body: ForgeMergeBody):
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

            cur.execute(f"SELECT * FROM {ZOOPARK_ITEMS_TABLE} WHERE id IN (%s,%s) AND user_id=%s", (item_id1, item_id2, user_id))
            rows = cur.fetchall()
            if len(rows) < 2:
                raise HTTPException(404, "Предметы не найдены")

            by_id = {int(r["id"]): r for r in rows}
            item1, item2 = by_id[item_id1], by_id[item_id2]

            for it in (item1, item2):
                if it["rarity"] == "legendary":
                    raise HTTPException(400, "Легендарные предметы нельзя объединять")

            props1: list[dict] = json.loads(item1["properties"]) if item1["properties"] else []
            props2: list[dict] = json.loads(item2["properties"]) if item2["properties"] else []
            n1, n2 = len(props1), len(props2)
            level1, level2 = int(item1["lvl"]), int(item2["lvl"])

            cost_usd = FORGE_MERGE_BASE_USD * (n1 + n2 + max(level1 + level2, 1))
            if int(user["usd"]) < cost_usd:
                raise HTTPException(400, f"Нужно ${cost_usd:,}")

            # Merge algorithm per game rules
            result_props: list[dict] = []
            rounds = max(n1, n2)
            success_prob = max(0, 100 - 10 * (n1 + n2))

            def _add_to_result(prop: dict) -> None:
                existing = next((p for p in result_props if p["type"] == prop["type"]), None)
                if existing:
                    existing["value"] += prop.get("value", 0)
                    _rebuild_label(existing)
                else:
                    result_props.append(dict(prop))

            for _ in range(rounds):
                if random.randint(1, 100) <= success_prob:
                    if props1:
                        _add_to_result(random.choice(props1))
                    if props2:
                        _add_to_result(random.choice(props2))
                else:
                    source = random.choice([s for s in (props1, props2) if s] or [props1])
                    if source:
                        _add_to_result(random.choice(source))

            # Cap at 5 properties (legendary limit)
            result_props = result_props[:5]
            new_count = max(1, len(result_props))
            new_rarity = RARITY_FROM_COUNT.get(new_count, "common")

            new_usd = int(user["usd"]) - cost_usd
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET usd=%s WHERE id=%s", (new_usd, user_id))
            cur.execute(f"DELETE FROM {ZOOPARK_ITEMS_TABLE} WHERE id IN (%s,%s)", (item_id1, item_id2))

            emoji = RARITY_ICONS[new_rarity]
            name = f"{RARITY_NAMES[new_rarity]} артефакт"
            cur.execute(
                f"INSERT INTO {ZOOPARK_ITEMS_TABLE} (user_id, emoji, name, lvl, properties, rarity, is_active) VALUES (%s,%s,%s,0,%s,%s,0)",
                (user_id, emoji, name, json.dumps(result_props, ensure_ascii=False), new_rarity),
            )
            new_item_id = cur.lastrowid
        db.commit()
        return {
            "ok": True,
            "new_item": _item_dict(new_item_id, emoji, name, new_rarity, 0, result_props, False),
            "cost_usd": cost_usd,
            "new_usd": new_usd,
        }
    finally:
        db.close()


def api_forge_sell(tg_id: int, body: ForgeItemIdBody):
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

            cur.execute(f"SELECT id FROM {ZOOPARK_ITEMS_TABLE} WHERE id=%s AND user_id=%s", (item_id, user_id))
            if not cur.fetchone():
                raise HTTPException(404, "Предмет не найден")

            cur.execute(f"DELETE FROM {ZOOPARK_ITEMS_TABLE} WHERE id=%s", (item_id,))
            new_usd = int(user["usd"]) + FORGE_SELL_USD
            cur.execute(f"UPDATE {ZOOPARK_USERS_TABLE} SET usd=%s WHERE id=%s", (new_usd, user_id))
        db.commit()
        return {"ok": True, "earned_usd": FORGE_SELL_USD, "new_usd": new_usd}
    finally:
        db.close()


def api_forge_activate(tg_id: int, body: ForgeActivateBody):
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

            cur.execute(f"SELECT id, is_active FROM {ZOOPARK_ITEMS_TABLE} WHERE id=%s AND user_id=%s", (item_id, user["id"]))
            item = cur.fetchone()
            if not item:
                raise HTTPException(404, "Предмет не найден")

            currently_active = bool(item["is_active"])
            if not currently_active:
                cur.execute(f"SELECT COUNT(*) as cnt FROM {ZOOPARK_ITEMS_TABLE} WHERE user_id=%s AND is_active=1", (user["id"],))
                if int(cur.fetchone()["cnt"]) >= MAX_ACTIVE_ITEMS:
                    raise HTTPException(400, f"Максимум {MAX_ACTIVE_ITEMS} активных предмета. Деактивируй один.")

            cur.execute(f"UPDATE {ZOOPARK_ITEMS_TABLE} SET is_active=%s WHERE id=%s", (0 if currently_active else 1, item_id))
        db.commit()
        return {"ok": True, "is_active": not currently_active}
    finally:
        db.close()
