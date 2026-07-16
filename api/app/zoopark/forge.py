"""The forge.

Every property an item can roll is applied somewhere — see `ITEM_PROPERTIES[...]["applies_to"]`
and `test_every_item_property_is_applied`. Before this rewrite the forge sold artefacts
labelled "Общий доход +45%" for 350 PawCoins (that is, for Telegram Stars, that is, for
money) and no code anywhere read the number.
"""

from __future__ import annotations

from random import SystemRandom

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import Item, ItemProperty, ItemSet, ItemSetMember
from api.app.schemas.forge import (
    ForgeActivateBody,
    ForgeCreateBody,
    ForgeItemIdBody,
    ForgeMergeBody,
    ForgeSetBody,
    ForgeSetIdBody,
)
from api.app.zoopark import ledger
from api.app.zoopark.catalog import (
    FORGE_CREATE_COUNTER_EPOCH,
    FORGE_CREATE_PAW,
    forge_create_cost_usd,
    FORGE_MAX_ACTIVE_ITEMS,
    FORGE_MAX_ITEM_LEVEL,
    FORGE_MERGE_COST_USD,
    FORGE_UPGRADE_BASE_USD,
    FORGE_UPGRADE_FAIL_PCT_PER_LEVEL,
    ITEM_PROPERTIES,
    ITEM_RARITY_BY_PROPERTY_COUNT,
    ITEM_RARITY_DROP_WEIGHTS,
    ITEM_RARITY_ICON,
    ITEM_RARITY_NAME,
    ITEM_PROPERTY_COUNT,
    PROPERTY_KINDS,
    SPECIES,
    SPECIES_ID_BY_CODE,
    ItemOrigin,
    ItemRarity,
    expedition_item_rarity_weights,
    PropertyKind,
    item_sell_price_usd,
)
from api.app.zoopark.income import sync_player_income
from api.app.zoopark.profile import get_player, item_payload, list_item_sets, list_items

random = SystemRandom()

_DROPPABLE_RARITIES: tuple[ItemRarity, ...] = ("common", "rare", "epic", "mythical")
_SPECIES_IDS = [SPECIES_ID_BY_CODE[s["code"]] for s in SPECIES]


# ─── Rolling an item ──────────────────────────────────────────────────────────


def _roll_rarity() -> ItemRarity:
    return random.choices(_DROPPABLE_RARITIES, weights=ITEM_RARITY_DROP_WEIGHTS)[0]


def _roll_properties(rarity: ItemRarity) -> list[tuple[PropertyKind, int, int | None]]:
    """`ITEM_PROPERTY_COUNT[rarity]` distinct kinds, each with a value and maybe a species."""
    kinds = list(PROPERTY_KINDS)
    weights = [ITEM_PROPERTIES[k]["weight"] for k in kinds]
    chosen: list[PropertyKind] = []
    for _ in range(ITEM_PROPERTY_COUNT[rarity]):
        if not kinds:
            break
        kind = random.choices(kinds, weights=weights)[0]
        index = kinds.index(kind)
        kinds.pop(index)
        weights.pop(index)
        chosen.append(kind)

    rolled: list[tuple[PropertyKind, int, int | None]] = []
    for kind in chosen:
        spec = ITEM_PROPERTIES[kind]
        low, high = spec["ranges"][rarity]
        species_id = random.choice(_SPECIES_IDS) if spec["per_species"] else None
        rolled.append((kind, random.randint(low, high), species_id))
    return rolled


def _item_name(rarity: ItemRarity) -> tuple[str, str]:
    return f"{ITEM_RARITY_NAME[rarity]} артефакт", ITEM_RARITY_ICON[rarity]


def roll_expedition_item(session: Session, player_id: int, depth: int) -> Item:
    """Create the item a raid at `depth` found, owned by the player and inactive.

    Lives here rather than in `progression` so there stays exactly one place that knows how
    an item is rolled and written. The rarity table is the depth's, not the forge's, and the
    origin marks it as found — which is what stops it being sold for a price it never cost.
    """
    rarity = random.choices(_DROPPABLE_RARITIES, weights=expedition_item_rarity_weights(depth))[0]
    return _add_item(session, player_id, rarity, _roll_properties(rarity), origin="expedition")


def _add_item(
    session: Session,
    player_id: int,
    rarity: ItemRarity,
    properties: list[tuple[PropertyKind, int, int | None]],
    origin: ItemOrigin = "forge",
) -> Item:
    name, emoji = _item_name(rarity)
    item = Item(
        player_id=player_id, rarity=rarity, level=0, name=name, emoji=emoji,
        is_active=False, origin=origin,
    )
    session.add(item)
    session.flush()
    for kind, value, species_id in properties:
        session.add(ItemProperty(item_id=item.id, kind=kind, value=value, species_id=species_id))
    session.flush()
    session.refresh(item)
    return item


# ─── Reads ────────────────────────────────────────────────────────────────────


def forge_items(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        return {"items": list_items(session, player.id)}


def forge_sets(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        return {"sets": list_item_sets(session, player.id)}


# ─── Create, upgrade, merge, sell ─────────────────────────────────────────────


def forge_create(tg_id: int, body: ForgeCreateBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        # Price escalates with how many items the player has created since the counter epoch,
        # counted from the ledger — so selling or merging items away never cheapens the next
        # creation. See FORGE_CREATE_COUNTER_EPOCH for why it is not counted from all time.
        creations = ledger.count_by_reason(
            session, player.id, "forge_create", since=FORGE_CREATE_COUNTER_EPOCH
        )
        rarity = _roll_rarity()
        properties = _roll_properties(rarity)

        if body.currency == "paw":
            ledger.spend(session, player, "paw", FORGE_CREATE_PAW, "forge_create")
            cost = {"cost_paw": FORGE_CREATE_PAW, "cost_usd": None}
        else:
            usd_cost = forge_create_cost_usd(creations)
            ledger.spend(session, player, "usd", usd_cost, "forge_create")
            cost = {"cost_paw": None, "cost_usd": usd_cost}

        item = _add_item(session, player.id, rarity, properties)
        payload = item_payload(item)
        result = {
            "ok": True,
            "item": payload,
            **cost,
            "new_usd": ledger.balance(player, "usd"),
            "new_paw_coins": ledger.balance(player, "paw"),
        }
        session.commit()
        return result


def upgrade_cost_usd(level: int) -> int:
    return FORGE_UPGRADE_BASE_USD * (level + 1)


def upgrade_success_pct(level: int) -> int:
    return max(0, 100 - FORGE_UPGRADE_FAIL_PCT_PER_LEVEL * level)


def forge_upgrade(tg_id: int, body: ForgeItemIdBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        item = session.scalars(
            select(Item).where(Item.id == body.item_id, Item.player_id == player.id).with_for_update()
        ).first()
        if not item:
            raise HTTPException(404, "Предмет не найден")
        if item.level >= FORGE_MAX_ITEM_LEVEL:
            raise HTTPException(400, f"Максимальный уровень {FORGE_MAX_ITEM_LEVEL}")
        if not item.properties:
            raise HTTPException(400, "У предмета нет свойств для улучшения")

        cost = upgrade_cost_usd(item.level)
        success_pct = upgrade_success_pct(item.level)
        ledger.spend(session, player, "usd", cost, "forge_upgrade")

        succeeded = random.randint(1, 100) <= success_pct
        if succeeded:
            item.level += 1
            random.choice(item.properties).value += 1

        session.flush()
        session.refresh(item)
        payload = item_payload(item)
        # Item bonuses feed income, so an upgraded active item changes it immediately.
        sync_player_income(session, player)
        result = {
            "ok": True,
            "success": succeeded,
            "success_pct": success_pct,
            "item": payload,
            "cost_usd": cost,
            "new_usd": ledger.balance(player, "usd"),
        }
        session.commit()
        return result


def merge_cost_usd() -> int:
    return FORGE_MERGE_COST_USD


def _merge_properties(a: list[ItemProperty], b: list[ItemProperty]) -> list[tuple[PropertyKind, int, int | None]]:
    """Same shape as the Telegram bot's `merge_items`: on a success both parents give up a
    property, on a failure only one does. Identical (kind, species) pairs stack."""
    pool_a = list(a)
    pool_b = list(b)
    success_pct = max(0, 100 - 10 * (len(pool_a) + len(pool_b)))
    merged: dict[tuple[str, int | None], int] = {}

    def take(pool: list[ItemProperty]) -> None:
        if not pool:
            return
        chosen = pool.pop(random.randrange(len(pool)))
        key = (chosen.kind, chosen.species_id)
        merged[key] = merged.get(key, 0) + chosen.value

    for _ in range(max(len(a), len(b))):
        if random.randint(1, 100) <= success_pct:
            take(pool_a)
            take(pool_b)
        else:
            take(random.choice([pool for pool in (pool_a, pool_b) if pool] or [pool_a]))

    ordered = sorted(merged.items(), key=lambda kv: -kv[1])[:5]
    return [(kind, value, species_id) for (kind, species_id), value in ordered]  # type: ignore[misc]


def forge_merge(tg_id: int, body: ForgeMergeBody) -> dict:
    first, second = body.item_id1, body.item_id2
    if first == second:
        raise HTTPException(400, "Нельзя объединить предмет сам с собой")

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        items = session.scalars(
            select(Item).where(Item.id.in_([first, second]), Item.player_id == player.id).with_for_update()
        ).all()
        by_id = {item.id: item for item in items}
        if len(by_id) != 2:
            raise HTTPException(404, "Предметы не найдены")

        item_a, item_b = by_id[first], by_id[second]
        for item in (item_a, item_b):
            if item.rarity == "legendary":
                raise HTTPException(400, "Легендарные предметы нельзя объединять")

        cost = merge_cost_usd()
        ledger.spend(session, player, "usd", cost, "forge_merge")

        properties = _merge_properties(list(item_a.properties), list(item_b.properties))
        rarity = ITEM_RARITY_BY_PROPERTY_COUNT[max(1, len(properties))]
        # A found item stays found through a merge. Laundering one into a sellable "forge"
        # item is a loss today only because the $100k fee happens to exceed the $32k resale —
        # an accident of two numbers, not a rule. Carrying the origin makes it a rule.
        origin: ItemOrigin = (
            "expedition" if "expedition" in (item_a.origin, item_b.origin) else "forge"
        )

        session.delete(item_a)
        session.delete(item_b)
        session.flush()

        new_item = _add_item(session, player.id, rarity, properties, origin)
        payload = item_payload(new_item)
        sync_player_income(session, player)
        result = {
            "ok": True,
            "new_item": payload,
            "cost_usd": cost,
            "new_usd": ledger.balance(player, "usd"),
        }
        session.commit()
        return result


def forge_sell(tg_id: int, body: ForgeItemIdBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        item = session.scalars(
            select(Item).where(Item.id == body.item_id, Item.player_id == player.id).with_for_update()
        ).first()
        if not item:
            raise HTTPException(404, "Предмет не найден")

        earned = item_sell_price_usd(item.rarity, item.level, item.origin)  # type: ignore[arg-type]
        session.delete(item)
        session.flush()
        ledger.grant(session, player, "usd", earned, "forge_sell")
        sync_player_income(session, player)
        result = {"ok": True, "earned_usd": earned, "new_usd": ledger.balance(player, "usd")}
        session.commit()
        return result


def forge_activate(tg_id: int, body: ForgeActivateBody) -> dict:
    try:
        item_id = body.resolved_item_id()
    except ValueError as exc:
        raise HTTPException(400, "Не указан предмет") from exc

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        item = session.scalars(
            select(Item).where(Item.id == item_id, Item.player_id == player.id).with_for_update()
        ).first()
        if not item:
            raise HTTPException(404, "Предмет не найден")

        if not item.is_active:
            active = session.scalar(
                select(func.count(Item.id)).where(Item.player_id == player.id, Item.is_active.is_(True))
            ) or 0
            if active >= FORGE_MAX_ACTIVE_ITEMS:
                raise HTTPException(400, f"Максимум {FORGE_MAX_ACTIVE_ITEMS} активных предмета. Деактивируй один.")

        item.is_active = not item.is_active
        is_active = item.is_active
        sync_player_income(session, player)
        result = {"ok": True, "is_active": is_active, "income_rub_per_min": player.income_rub_per_min}
        session.commit()
        return result


# ─── Sets ─────────────────────────────────────────────────────────────────────


def _owned_item_ids(session: Session, player_id: int, item_ids: list[int]) -> list[int]:
    if len(item_ids) > FORGE_MAX_ACTIVE_ITEMS:
        raise HTTPException(400, f"Максимум {FORGE_MAX_ACTIVE_ITEMS} предмета в сете")
    if not item_ids:
        return []
    owned = set(
        session.scalars(select(Item.id).where(Item.player_id == player_id, Item.id.in_(item_ids))).all()
    )
    missing = [i for i in item_ids if i not in owned]
    if missing:
        raise HTTPException(404, "Предмет не найден")
    return item_ids


def forge_set_create(tg_id: int, body: ForgeSetBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")

        item_ids = _owned_item_ids(session, player.id, body.unique_item_ids())
        existing = session.scalar(select(func.count(ItemSet.id)).where(ItemSet.player_id == player.id)) or 0
        item_set = ItemSet(
            player_id=player.id,
            name=(body.name or f"Сет {existing + 1}")[:32],
            emoji=(body.icon or "⚒️")[:16],
        )
        session.add(item_set)
        try:
            session.flush()
        except IntegrityError as exc:
            raise HTTPException(400, "Сет с таким названием уже есть") from exc

        for position, item_id in enumerate(item_ids):
            session.add(ItemSetMember(set_id=item_set.id, item_id=item_id, position=position))

        session.flush()
        payload = {
            "id": str(item_set.id),
            "name": item_set.name,
            "icon": item_set.emoji,
            "item_ids": [str(i) for i in item_ids],
            "is_active": False,
        }
        session.commit()
        return {"ok": True, "set": payload}


def _get_set(session: Session, player_id: int, set_id: int) -> ItemSet:
    item_set = session.scalars(
        select(ItemSet).where(ItemSet.id == set_id, ItemSet.player_id == player_id)
    ).first()
    if not item_set:
        raise HTTPException(404, "Сет не найден")
    return item_set


def forge_set_update(tg_id: int, body: ForgeSetBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        if body.set_id is None:
            raise HTTPException(400, "Неверный ID")

        item_set = _get_set(session, player.id, body.set_id)
        item_ids = _owned_item_ids(session, player.id, body.unique_item_ids())

        if body.name:
            item_set.name = body.name[:32]
        if body.icon:
            item_set.emoji = body.icon[:16]

        session.query(ItemSetMember).filter(ItemSetMember.set_id == item_set.id).delete()
        for position, item_id in enumerate(item_ids):
            session.add(ItemSetMember(set_id=item_set.id, item_id=item_id, position=position))

        session.flush()
        payload = {
            "id": str(item_set.id),
            "name": item_set.name,
            "icon": item_set.emoji,
            "item_ids": [str(i) for i in item_ids],
        }
        session.commit()
        return {"ok": True, "set": payload}


def forge_set_delete(tg_id: int, body: ForgeSetIdBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        session.delete(_get_set(session, player.id, body.set_id))
        session.commit()
        return {"ok": True}


def forge_set_apply(tg_id: int, body: ForgeSetIdBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        item_set = _get_set(session, player.id, body.set_id)
        wanted = {member.item_id for member in item_set.members}
        if len(wanted) > FORGE_MAX_ACTIVE_ITEMS:
            raise HTTPException(400, f"Максимум {FORGE_MAX_ACTIVE_ITEMS} активных предмета")

        for item in session.scalars(select(Item).where(Item.player_id == player.id).with_for_update()).all():
            item.is_active = item.id in wanted

        sync_player_income(session, player)
        result = {"ok": True, "income_rub_per_min": player.income_rub_per_min}
        session.commit()
        return result
