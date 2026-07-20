"""The rival's dream: an offline pass that consolidates its notebook between turns.

A turn only ever *appends* notes, and the model tends to write the current balance down
each time — so the notebook fills with restatements of state that any tool could read live,
and the durable lessons underneath ("экспедиция глубины 1 разгромила отряд") get pushed
toward eviction by them. Left alone it degrades into a worse transcript of a transcript.

This is the reflection step from Generative Agents (Park et al.) run as what the agent-memory
literature now calls *dreaming* or *sleep-time consolidation*: not on the turn's critical
path, but between turns, a separate model call takes the accumulated notes and distils them
into a smaller set of higher-order conclusions — merging duplicates, dropping what a newer
note contradicts, and throwing away pure state. The raw notebook is snapshotted first, so a
bad consolidation is recoverable.

It is *pressure-triggered*: it runs only once the notebook has grown past a threshold, well
before the hard `MAX_NOTES` cap, so a dream costs one extra model call every many turns
rather than one per turn. If the model is unreachable or answers with nothing usable, the
notebook is left exactly as it was — a bloated notebook beats a wiped one.
"""

from __future__ import annotations

import json
import logging

from api.app.core.config import BOT_PLANNER_MODEL
from api.bots import agent, memory_store

logger = logging.getLogger(__name__)

# Dream once the notebook reaches this many notes — comfortably below memory_store.MAX_NOTES
# (40), so consolidation happens before eviction starts throwing lessons away.
DREAM_AFTER_NOTES = 24
# The model is asked to come back with at most this many conclusions. Fewer, denser notes is
# the whole point; the cap keeps a dream from just reprinting the input.
DREAM_TARGET_NOTES = 12
MAX_TOKENS = 4000

_SYSTEM = (
    "Ты помогаешь игроку привести в порядок его заметки о собственной игре в браузерном "
    "зоопарке. Тебе дают список того, что он записывал по ходу партии. Верни сжатую выжимку "
    "выводов — то, что стоит помнить дальше."
)


def _prompt(notes: list[dict]) -> str:
    lines = "\n".join(f"[{i}] {n.get('когда', '')} — {n.get('заметка', '')}" for i, n in enumerate(notes))
    return (
        f"Вот заметки игрока, самые старые сверху:\n\n{lines}\n\n"
        f"Сожми их не более чем в {DREAM_TARGET_NOTES} выводов. Правила:\n"
        f"— Оставляй только то, что пригодится в будущих ходах: что сработало, что оказалось "
        f"ошибкой, устойчивая стратегия, факты о мире игры, которые не меняются.\n"
        f"— Выкидывай баланс, доход, курс, «сколько осталось до» и прочее состояние: это "
        f"всегда можно посмотреть инструментами прямо в ходе, и к следующему ходу оно устареет.\n"
        f"— Если поздняя заметка противоречит ранней, верь поздней, раннюю выброси.\n"
        f"— Объединяй повторяющиеся мысли в одну.\n"
        f"— Пиши от первого лица, коротко, по одной мысли на пункт.\n\n"
        f'Ответь СТРОГО одним JSON-массивом строк и ничем больше, например: '
        f'["вывод один", "вывод два"]'
    )


def _extract(data: dict) -> list[str]:
    """Pull the JSON array of conclusions out of the model's reply, tolerating the prose or
    code fence a reasoning model sometimes wraps it in. Returns [] on anything unparseable —
    the caller treats that as "don't touch the notebook"."""
    try:
        content = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return []
    start, end = content.find("["), content.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        parsed = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    lessons = [str(item).strip() for item in parsed if str(item).strip()]
    return lessons[:DREAM_TARGET_NOTES]


def run_dream(player_id: int, *, ask=agent._ask, force: bool = False) -> dict:
    """Consolidate one rival's notebook if it has grown enough. Never raises."""
    notes = memory_store.load(player_id)
    if not force and len(notes) < DREAM_AFTER_NOTES:
        return {"ok": True, "dreamed": False, "заметок": len(notes)}

    data = ask({
        "model": BOT_PLANNER_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _prompt(notes)},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
    })
    if data is None:
        logger.warning("bot %s: сон не удался — модель недоступна, заметки не тронуты", player_id)
        return {"ok": False, "dreamed": False, "error": "модель недоступна"}

    lessons = _extract(data)
    if not lessons:
        logger.warning("bot %s: сон не дал разбираемых выводов, заметки не тронуты", player_id)
        return {"ok": False, "dreamed": False, "error": "нечего записать"}

    memory_store.snapshot(player_id)
    memory_store.overwrite(player_id, [memory_store.make_note(text) for text in lessons])
    logger.info("bot %s: сон свёл %d заметок в %d выводов", player_id, len(notes), len(lessons))
    return {"ok": True, "dreamed": True, "было": len(notes), "стало": len(lessons)}
