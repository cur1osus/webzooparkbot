"""A compact, deterministic state view for the rival's next decision.

The model still has the detailed tools for drilling into a question. This view is the
cheap first pass: it exposes the facts that usually decide a turn without making the model
spend a round on every screen in the game.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from api.app.zoopark import core as core_service
from api.app.zoopark import economy as economy_service
from api.app.zoopark import forge as forge_service
from api.app.zoopark import merchant as merchant_service
from api.app.zoopark import progression as progression_service
from api.app.zoopark import safe as safe_service
from api.app.zoopark import status as status_service
from api.app.zoopark.catalog import HABITATS

logger = logging.getLogger(__name__)


def _read(name: str, fn: Callable[[], dict], errors: list[str]) -> dict:
    try:
        value = fn()
        return value if isinstance(value, dict) else {}
    except Exception:  # noqa: BLE001 — one stale screen must not lose the whole snapshot
        logger.exception("snapshot: не удалось прочитать %s", name)
        errors.append(name)
        return {}


def _animal_brief(animal: dict[str, Any], *, locality_habitat: str | None = None) -> dict[str, Any]:
    habitat = animal.get("habitat")
    return {
        "id": animal.get("id"),
        "имя": animal.get("name"),
        "вид": animal.get("species_code"),
        "среда": habitat,
        "локация": locality_habitat,
        "выживаемость": animal.get("survival"),
        "болен": bool(animal.get("is_sick", False)),
        "доход": animal.get("income"),
        "умрёт": animal.get("dies_at"),
    }


def _as_utc(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def build(tg_id: int, *, now: datetime | None = None) -> dict[str, Any]:
    """Return the current facts most useful for choosing one game objective."""
    now = now or datetime.now(timezone.utc)
    errors: list[str] = []
    me = _read("me", lambda: core_service.me(tg_id), errors)
    localities = _read("localities", lambda: progression_service.list_localities(tg_id), errors)
    animals_payload = _read("animals", lambda: progression_service.list_available_animals(tg_id), errors)
    packs = _read("packs", lambda: progression_service.packs_info(tg_id), errors)
    bank = _read("bank", lambda: economy_service.bank(tg_id), errors)
    forge = _read("forge", lambda: forge_service.forge_items(tg_id), errors)
    expeditions = _read("expeditions", lambda: progression_service.get_expeditions(tg_id), errors)
    merchant = _read("merchant", lambda: merchant_service.merchant_animals(tg_id), errors)
    safe = _read("safe", lambda: safe_service.safe_state(tg_id), errors)
    bonus = _read("bonus", lambda: status_service.daily_bonus(tg_id), errors)

    localities_rows = localities.get("localities") or []
    animals = animals_payload.get("animals") or []
    habitat_by_animal: dict[int, str] = {}
    animals_in_locality: dict[int, list[dict]] = {}
    for locality in localities_rows:
        locality_id = locality.get("id")
        animals_in_locality[locality_id] = locality.get("animals") or []
        for animal in animals_in_locality[locality_id]:
            if animal.get("id") is not None:
                habitat_by_animal[int(animal["id"])] = locality.get("habitat")

    unassigned = [animal for animal in animals if not animal.get("locality_id")]
    misplaced = [
        animal for animal in animals
        if animal.get("locality_id")
        and habitat_by_animal.get(int(animal.get("id"))) != animal.get("habitat")
    ]
    sick = [animal for animal in animals if animal.get("is_sick", False)]
    weak = [animal for animal in animals if animal.get("survival") == "low"]
    soonest = sorted(
        (animal for animal in animals if animal.get("dies_at")),
        key=lambda animal: str(animal.get("dies_at")),
    )[:5]
    critical_deaths = [
        animal for animal in animals
        if (dies_at := _as_utc(animal.get("dies_at"))) is not None
        and now <= dies_at <= now + timedelta(hours=6)
    ]

    owned_habitats = {locality.get("habitat") for locality in localities_rows}
    finished_expeditions = [
        expedition for expedition in expeditions.get("expeditions", [])
        if expedition.get("status") == "finished"
    ]

    merchant_rows = merchant.get("animals") or []
    merchant_brief = [
        {
            "слот": row.get("slot", index),
            "имя": row.get("name"),
            "вид": row.get("species_code"),
            "цена": row.get("price_usd", row.get("price")),
            "выживаемость": row.get("survival"),
            "среда": row.get("habitat"),
        }
        for index, row in enumerate(merchant_rows, 1)
    ]
    pack_brief = [
        {
            "тир": row.get("tier"),
            "доступен": bool(row.get("unlocked")),
            "цена_1_usd": row.get("price"),
            "цена_50_usd": (row.get("batch_prices") or {}).get("50"),
            "цена_100_usd": (row.get("batch_prices") or {}).get("100"),
            "диапазон_награды": row.get("reward_range"),
        }
        for row in (packs.get("tiers") or [])
    ]

    snapshot: dict[str, Any] = {
        "ok": True,
        "срез_на": datetime.now(timezone.utc).isoformat(),
        "игрок": {
            "ник": me.get("nickname"),
            "рубли": me.get("rub", me.get("balance_rub")),
            "доллары": me.get("usd", me.get("balance_usd")),
            "лапки": me.get("paw_coins", me.get("balance_paw")),
            "доход_руб_мин": me.get("income_rub_per_min"),
            "содержание_руб_мин": me.get("upkeep_rub_per_min"),
        },
        "зоопарк": {
            "зверей": len(animals),
            "больных": len(sick),
            "слабых_low_survival": len(weak),
            "умирают_в_6ч": len(critical_deaths),
            "потеря_дохода_руб_мин_в_6ч": sum(
                int(animal.get("income") or 0) for animal in critical_deaths
            ),
            "без_локации": len(unassigned),
            "не_в_своей_среде": len(misplaced),
            "ближайшие_смерти": [_animal_brief(animal) for animal in soonest],
            "проблемные_звери": [
                _animal_brief(animal, locality_habitat=habitat_by_animal.get(int(animal.get("id"))))
                for animal in (sick + misplaced)[:10]
            ],
        },
        "локации": [
            {
                "id": locality.get("id"),
                "среда": locality.get("habitat"),
                "уровень": locality.get("level"),
                "зверей": len(locality.get("animals") or []),
            }
            for locality in localities_rows
        ],
        "кузница": {
            "предметов": len(forge.get("items") or []),
            "активных": forge.get("active_item_count", 0),
            "активные_бонусы": forge.get("active_item_bonuses") or [],
            "стоимость_следующего_usd": forge.get("next_cost_usd"),
            "стоимость_лапками": forge.get("cost_paw"),
            "можно_создать_за_usd": (
                me.get("usd") is not None
                and forge.get("next_cost_usd") is not None
                and me["usd"] >= forge["next_cost_usd"]
            ),
            "можно_создать_за_лапки": (
                me.get("paw_coins") is not None
                and forge.get("cost_paw") is not None
                and me["paw_coins"] >= forge["cost_paw"]
            ),
        },
        "свободные_среды": sorted(set(HABITATS) - owned_habitats),
        "возможности": {
            "бесплатный_пак": bool(packs.get("gift_available")),
            "платные_паки": pack_brief,
            "бонус_забран": bonus.get("claimed"),
            "готовые_экспедиции": [
                {"id": expedition.get("id"), "среда": expedition.get("habitat"), "глубина": expedition.get("depth")}
                for expedition in finished_expeditions
            ],
            "курс_руб_за_usd": bank.get("rate_rub_per_usd"),
            "история_курса": (bank.get("history") or [])[-5:],
            "сейф": {
                key: safe.get(key)
                for key in ("is_open", "opens_at", "closes_at", "attempts_left", "prize_usd")
                if key in safe
            },
            "торговец": merchant_brief[:6],
        },
    }
    if errors:
        snapshot["не_прочитано"] = errors
    return snapshot
