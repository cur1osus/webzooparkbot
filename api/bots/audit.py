"""The auditor: a look at the books that the rival does not get to narrate.

A turn ends with the model writing its own summary, and the model is a generous witness to
itself. On 2026-07-21 a turn closed with «все звери при своих средах (бонус x1.5)» while
fourteen of forty animals stood outside their habitat — nine of them with an empty matching
locality already bought and waiting. Nothing in the loop could contradict it: the next turn
began from that summary and the notebook it fed.

So the auditor runs at the *start* of every turn, before the model has said anything, and
reads the same database a player's screen reads. What it returns are not opinions and not
advice — they are facts with ids attached, and they go into the opening message. The rival
can decide they do not matter. It can no longer claim they are not there.

Deliberately not a model call. The failure being corrected is a model describing state it
had just read; asking a second model to check the first would add a second thing that can
be wrong, and a per-turn cost, to catch something arithmetic already catches for free.

Findings are ordered by what they cost: money already lost, then money about to be lost,
then money sitting idle.
"""

from __future__ import annotations

import logging

from api.app.zoopark import core as core_service
from api.app.zoopark import progression as progression_service
from api.app.zoopark import status as status_service

logger = logging.getLogger(__name__)

# Below this the upkeep is not worth a line of the opening message.
THIN_MARGIN_PERCENT = 70


def _names(animals: list[dict], limit: int = 6) -> str:
    shown = ", ".join(f"{a['name']} (id {a['id']})" for a in animals[:limit])
    return shown if len(animals) <= limit else f"{shown} и ещё {len(animals) - limit}"


def findings(tg_id: int) -> list[str]:
    """Everything wrong with this zoo right now, in plain sentences. Never raises."""
    out: list[str] = []
    try:
        localities = progression_service.list_localities(tg_id)
        me = core_service.me(tg_id)
    except Exception:
        logger.exception("ревизор не смог прочитать состояние игрока %s", tg_id)
        return []

    owned = {loc["habitat"]: loc for loc in localities["localities"]}
    misplaced_with_home: list[dict] = []
    misplaced_homeless: dict[str, list[dict]] = {}
    sick: list[dict] = []

    for loc in localities["localities"]:
        for animal in loc["animals"]:
            if animal["is_sick"]:
                sick.append(animal)
            if animal["habitat"] != loc["habitat"]:
                if animal["habitat"] in owned:
                    misplaced_with_home.append(animal)
                else:
                    misplaced_homeless.setdefault(animal["habitat"], []).append(animal)

    unassigned = localities["unassigned"]
    sick.extend(a for a in unassigned if a["is_sick"])

    if misplaced_with_home:
        by_habitat: dict[str, list[dict]] = {}
        for animal in misplaced_with_home:
            by_habitat.setdefault(animal["habitat"], []).append(animal)
        for habitat, animals in sorted(by_habitat.items()):
            out.append(
                f"{len(animals)} зверей среды «{habitat}» сидят не в своей локации, "
                f"хотя локация {habitat} у тебя есть (id {owned[habitat]['id']}). "
                f"Каждый недодаёт треть дохода: {_names(animals)}."
            )

    if unassigned:
        out.append(
            f"{len(unassigned)} зверей вообще без локации — они дают ноль: {_names(unassigned)}."
        )

    for habitat, animals in sorted(misplaced_homeless.items()):
        out.append(
            f"{len(animals)} зверей среды «{habitat}» негде поселить — такой локации нет. "
            f"Купить её стоит {localities['next_price']} ₽." if localities.get("next_price")
            else f"{len(animals)} зверей среды «{habitat}» негде поселить, и локации кончились."
        )

    if sick:
        out.append(f"{len(sick)} больных зверей: приносят вдвое меньше и заражают соседей — {_names(sick)}.")

    income = int(me["income_rub_per_min"])
    upkeep = int(me["upkeep_rub_per_min"])
    if income and upkeep * 100 >= income * THIN_MARGIN_PERCENT:
        out.append(
            f"Содержание {upkeep} ₽/мин против дохода {income} ₽/мин — "
            f"запас почти съеден. Слабых зверей дешевле отпустить, чем содержать."
        )

    try:
        if progression_service.packs_info(tg_id)["gift_available"]:
            out.append("Бесплатный пак за сегодня не открыт.")
        if not status_service.daily_bonus(tg_id)["claimed"]:
            out.append("Ежедневный бонус за сегодня не забран.")
        if progression_service.has_collectible_expedition(tg_id):
            out.append("Экспедиция вернулась, добыча не забрана.")
    except Exception:
        logger.exception("ревизор не смог прочитать дневные выдачи игрока %s", tg_id)

    return out


def as_text(tg_id: int) -> str:
    """The block that goes into the opening message, or an empty string when all is well."""
    lines = findings(tg_id)
    if not lines:
        return ""
    numbered = "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))
    return (
        "РЕВИЗОР ОСМОТРЕЛ ТВОЙ ЗООПАРК ПЕРЕД ХОДОМ.\n"
        "Это проверенные факты из базы, а не твои воспоминания — если они расходятся с тем, "
        "что ты записал в заметках, прав ревизор.\n"
        f"{numbered}\n"
        "Разберись с этим или сознательно реши, что сейчас важнее другое."
    )
