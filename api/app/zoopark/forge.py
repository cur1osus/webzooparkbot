from __future__ import annotations

import json
import random
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import ForgeSet, ForgeSetItem, Item, User
from api.app.schemas.forge import ForgeActivateBody, ForgeCreateBody, ForgeItemIdBody, ForgeMergeBody, ForgeSetBody, ForgeSetIdBody
from api.app.zoopark.catalog import ANIMALS
from api.app.zoopark.profile import bump_data_version, get_forge_items, get_forge_sets, get_user

ANIMAL_IDS = [a["id"] for a in ANIMALS]
ANIMAL_NAMES: dict[str, str] = {a["id"]: a["name"] for a in ANIMALS}

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

FORGE_CREATE_BASE_USD = 1
FORGE_CREATE_PAW = 350
FORGE_CREATE_MULT = 1.15
FORGE_UPGRADE_BASE_USD = 30_000
FORGE_SELL_USD = 80_000
FORGE_MERGE_BASE_USD = 100_000
MAX_ITEM_LEVEL = 12
MAX_ACTIVE_ITEMS = 3


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


def _set_payload(raw: dict) -> dict:
    item_ids: list[str] = []
    for raw_id in raw.get("item_ids") or []:
        item_id = str(raw_id)
        if item_id not in item_ids:
            item_ids.append(item_id)
        if len(item_ids) >= MAX_ACTIVE_ITEMS:
            break
    return {
        "id": str(raw["id"]),
        "name": str(raw.get("name") or "Сет")[:32],
        "icon": str(raw.get("icon") or "⚒️")[:8],
        "item_ids": item_ids,
    }


def _save_forge_sets(session: Session, user_id: int, sets: list[dict]) -> None:
    bump_data_version(session, user_id)
    payload = [_set_payload(s) for s in sets]
    payload_keys = {str(item_set["id"]) for item_set in payload}
    existing = session.query(ForgeSet).filter(ForgeSet.user_id == user_id).all()
    by_key = {item_set.set_key: item_set for item_set in existing}

    for item_set in existing:
        if item_set.set_key not in payload_keys:
            session.delete(item_set)

    from datetime import datetime, timezone
    for item_set in payload:
        set_key = str(item_set["id"])
        db_set = by_key.get(set_key)
        if db_set is None:
            db_set = ForgeSet(
                user_id=user_id,
                set_key=set_key,
                name=item_set["name"],
                icon=item_set["icon"],
                created_at=datetime.now(timezone.utc),
            )
            session.add(db_set)
            session.flush()
        else:
            db_set.name = item_set["name"]
            db_set.icon = item_set["icon"]

        session.query(ForgeSetItem).filter(ForgeSetItem.set_id == db_set.id).delete()
        for position, item_id in enumerate(item_set["item_ids"]):
            session.add(ForgeSetItem(set_id=db_set.id, item_id=int(item_id), position=position))


def _validate_set_item_ids(item_ids: list[str], owned_ids: set[str]) -> list[str]:
    result: list[str] = []
    for raw_id in item_ids:
        item_id = str(raw_id)
        if item_id not in owned_ids:
            raise HTTPException(404, "Предмет не найден")
        if item_id not in result:
            result.append(item_id)
        if len(result) > MAX_ACTIVE_ITEMS:
            raise HTTPException(400, f"Максимум {MAX_ACTIVE_ITEMS} предмета в сете")
    return result


def _find_set(sets: list[dict], set_id: str) -> dict:
    item_set = next((s for s in sets if str(s["id"]) == str(set_id)), None)
    if not item_set:
        raise HTTPException(404, "Сет не найден")
    return item_set


def api_forge_items(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        return {"items": get_forge_items(session, user.id)}


def api_forge_sets(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        items = get_forge_items(session, user.id)
        return {"sets": get_forge_sets(session, user.id, items)}


def api_forge_set_create(tg_id: int, body: ForgeSetBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user_id = user.id
        items = get_forge_items(session, user_id)
        owned_ids = {str(item["id"]) for item in items}
        sets = get_forge_sets(session, user_id, items)
        item_ids = _validate_set_item_ids(getattr(body, "item_ids", []) or [], owned_ids)
        item_set = {
            "id": uuid.uuid4().hex[:10],
            "name": (getattr(body, "name", None) or f"Сет {len(sets) + 1}")[:32],
            "icon": (getattr(body, "icon", None) or "⚒️")[:8],
            "item_ids": item_ids,
        }
        sets.append(item_set)
        _save_forge_sets(session, user_id, sets)
        session.commit()
        return {"ok": True, "set": {**item_set, "is_active": False}}


def api_forge_set_update(tg_id: int, body: ForgeSetBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        if not getattr(body, "set_id", None):
            raise HTTPException(400, "Неверный ID")
        user_id = user.id
        items = get_forge_items(session, user_id)
        owned_ids = {str(item["id"]) for item in items}
        sets = get_forge_sets(session, user_id, items)
        item_set = _find_set(sets, str(body.set_id))
        item_set["item_ids"] = _validate_set_item_ids(getattr(body, "item_ids", []) or [], owned_ids)
        if getattr(body, "name", None):
            item_set["name"] = body.name[:32]
        if getattr(body, "icon", None):
            item_set["icon"] = body.icon[:8]
        _save_forge_sets(session, user_id, sets)
        session.commit()
        return {"ok": True, "set": item_set}


def api_forge_set_delete(tg_id: int, body: ForgeSetIdBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user_id = user.id
        items = get_forge_items(session, user_id)
        sets = get_forge_sets(session, user_id, items)
        _find_set(sets, body.set_id)
        sets = [s for s in sets if str(s["id"]) != str(body.set_id)]
        _save_forge_sets(session, user_id, sets)
        session.commit()
        return {"ok": True}


def api_forge_set_apply(tg_id: int, body: ForgeSetIdBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user_id = user.id
        items = get_forge_items(session, user_id)
        owned_ids = {str(item["id"]) for item in items}
        item_set = _find_set(get_forge_sets(session, user_id, items), body.set_id)
        item_ids = _validate_set_item_ids(item_set["item_ids"], owned_ids)
        active_int_ids = {int(iid) for iid in item_ids}
        for item in session.query(Item).filter(Item.user_id == user_id).all():
            item.is_active = 1 if item.id in active_int_ids else 0
        bump_data_version(session, user_id)
        session.commit()
        return {"ok": True}


def api_forge_create(tg_id: int, body: ForgeCreateBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user_id = user.id
        item_count = session.query(Item).filter(Item.user_id == user_id).count()

        usd_cost = int(FORGE_CREATE_BASE_USD * (FORGE_CREATE_MULT ** item_count))
        paw_cost = FORGE_CREATE_PAW
        currency = body.currency if body.currency in ("usd", "paw") else "usd"

        if currency == "paw":
            if user.paw_coins < paw_cost:
                raise HTTPException(400, f"Нужно {paw_cost} PawCoins")
            user.paw_coins -= paw_cost
            cost_usd_out = None
            cost_paw_out: int | None = paw_cost
        else:
            if user.usd < usd_cost:
                raise HTTPException(400, f"Нужно ${usd_cost:,}")
            user.usd -= usd_cost
            cost_usd_out: int | None = usd_cost
            cost_paw_out = None

        rarity = random.choices(RARITIES, RARITY_PROBS)[0]
        props = _make_properties(rarity)
        emoji = RARITY_ICONS[rarity]
        name = f"{RARITY_NAMES[rarity]} артефакт"

        new_item = Item(user_id=user_id, emoji=emoji, name=name, lvl=0, properties=json.dumps(props, ensure_ascii=False), rarity=rarity, is_active=0)
        session.add(new_item)
        session.flush()
        item_id = new_item.id
        session.commit()
        return {
            "ok": True,
            "item": _item_dict(item_id, emoji, name, rarity, 0, props, False),
            "cost_usd": cost_usd_out,
            "new_usd": user.usd,
            "cost_paw_coins": cost_paw_out,
            "new_paw_coins": user.paw_coins,
        }


def api_forge_upgrade(tg_id: int, body: ForgeItemIdBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user_id = user.id
        try:
            item_id = int(body.item_id)
        except ValueError as exc:
            raise HTTPException(400, "Неверный ID") from exc

        item = session.query(Item).filter(Item.id == item_id, Item.user_id == user_id).first()
        if not item:
            raise HTTPException(404, "Предмет не найден")

        level = item.lvl
        if level >= MAX_ITEM_LEVEL:
            raise HTTPException(400, f"Максимальный уровень {MAX_ITEM_LEVEL}")

        cost_usd = FORGE_UPGRADE_BASE_USD * (level + 1)
        if user.usd < cost_usd:
            raise HTTPException(400, f"Нужно ${cost_usd:,}")

        success_pct = max(0, 100 - 8 * level)
        success = random.randint(1, 100) <= success_pct
        user.usd -= cost_usd

        props: list[dict] = json.loads(item.properties) if item.properties else []
        new_level = level

        if success and props:
            new_level = level + 1
            idx = random.randint(0, len(props) - 1)
            props[idx] = dict(props[idx])
            props[idx]["value"] = props[idx].get("value", 0) + 1
            _rebuild_label(props[idx])
            item.lvl = new_level
            item.properties = json.dumps(props, ensure_ascii=False)

        session.commit()
        return {
            "ok": True,
            "success": success,
            "success_pct": success_pct,
            "item": _item_dict(item_id, item.emoji, item.name, item.rarity, new_level, props, bool(item.is_active)),
            "cost_usd": cost_usd,
            "new_usd": user.usd,
        }


def api_forge_merge(tg_id: int, body: ForgeMergeBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user_id = user.id
        try:
            item_id1 = int(body.item_id1)
            item_id2 = int(body.item_id2)
        except ValueError as exc:
            raise HTTPException(400, "Неверный ID") from exc

        if item_id1 == item_id2:
            raise HTTPException(400, "Нельзя объединить предмет сам с собой")

        items = session.query(Item).filter(Item.id.in_([item_id1, item_id2]), Item.user_id == user_id).all()
        if len(items) < 2:
            raise HTTPException(404, "Предметы не найдены")

        by_id = {item.id: item for item in items}
        item1, item2 = by_id[item_id1], by_id[item_id2]

        for it in (item1, item2):
            if it.rarity == "legendary":
                raise HTTPException(400, "Легендарные предметы нельзя объединять")

        props1: list[dict] = json.loads(item1.properties) if item1.properties else []
        props2: list[dict] = json.loads(item2.properties) if item2.properties else []
        n1, n2 = len(props1), len(props2)
        level1, level2 = item1.lvl, item2.lvl

        cost_usd = FORGE_MERGE_BASE_USD * (n1 + n2 + max(level1 + level2, 1))
        if user.usd < cost_usd:
            raise HTTPException(400, f"Нужно ${cost_usd:,}")

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

        result_props = result_props[:5]
        new_count = max(1, len(result_props))
        new_rarity = RARITY_FROM_COUNT.get(new_count, "common")

        user.usd -= cost_usd
        session.delete(item1)
        session.delete(item2)
        session.flush()

        emoji = RARITY_ICONS[new_rarity]
        name = f"{RARITY_NAMES[new_rarity]} артефакт"
        new_item = Item(user_id=user_id, emoji=emoji, name=name, lvl=0, properties=json.dumps(result_props, ensure_ascii=False), rarity=new_rarity, is_active=0)
        session.add(new_item)
        session.flush()
        new_item_id = new_item.id
        session.commit()
        return {
            "ok": True,
            "new_item": _item_dict(new_item_id, emoji, name, new_rarity, 0, result_props, False),
            "cost_usd": cost_usd,
            "new_usd": user.usd,
        }


def api_forge_sell(tg_id: int, body: ForgeItemIdBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user_id = user.id
        try:
            item_id = int(body.item_id)
        except ValueError as exc:
            raise HTTPException(400, "Неверный ID") from exc

        item = session.query(Item).filter(Item.id == item_id, Item.user_id == user_id).first()
        if not item:
            raise HTTPException(404, "Предмет не найден")

        session.delete(item)
        user.usd += FORGE_SELL_USD
        session.commit()
        return {"ok": True, "earned_usd": FORGE_SELL_USD, "new_usd": user.usd}


def api_forge_activate(tg_id: int, body: ForgeActivateBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        try:
            item_id = int(body.set_id)
        except ValueError as exc:
            raise HTTPException(400, "Неверный ID") from exc

        item = session.query(Item).filter(Item.id == item_id, Item.user_id == user.id).first()
        if not item:
            raise HTTPException(404, "Предмет не найден")

        currently_active = bool(item.is_active)
        if not currently_active:
            active_count = session.query(Item).filter(Item.user_id == user.id, Item.is_active == 1).count()
            if active_count >= MAX_ACTIVE_ITEMS:
                raise HTTPException(400, f"Максимум {MAX_ACTIVE_ITEMS} активных предмета. Деактивируй один.")

        item.is_active = 0 if currently_active else 1
        session.commit()
        return {"ok": True, "is_active": not currently_active}
