"""A small, player-owned library of reusable procedures.

Notes preserve observations. Skills preserve an executable pattern: when it applies, what
steps worked, and why. The model decides when a successful sequence is reusable; the harness
keeps the library bounded and replaces stale procedures by name.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from api.bots import memory_store

MAX_SKILLS = 12
MAX_NAME_CHARS = 80
MAX_TRIGGER_CHARS = 240
MAX_STEP_CHARS = 240
MAX_STEPS = 6
MAX_RATIONALE_CHARS = 300


def _path(player_id: int) -> Path:
    return memory_store.MEMORY_DIR / f"bot_{player_id}.skills.json"


def load(player_id: int) -> list[dict[str, Any]]:
    path = _path(player_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [skill for skill in data if isinstance(skill, dict)][:MAX_SKILLS]


def _write(player_id: int, skills: list[dict[str, Any]]) -> None:
    path = _path(player_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=path.name, suffix=".tmp", delete=False
    ) as handle:
        json.dump(skills[-MAX_SKILLS:], handle, ensure_ascii=False, indent=1)
        temporary = Path(handle.name)
    temporary.replace(path)


def save(
    player_id: int,
    name: str,
    trigger: str,
    steps: list[str],
    rationale: str = "",
) -> dict[str, Any]:
    name = (name or "").strip()[:MAX_NAME_CHARS]
    trigger = (trigger or "").strip()[:MAX_TRIGGER_CHARS]
    steps = [str(step).strip()[:MAX_STEP_CHARS] for step in (steps or []) if str(step).strip()]
    rationale = (rationale or "").strip()[:MAX_RATIONALE_CHARS]
    if not name or not trigger or not steps:
        return {"ok": False, "error": "у навыка нужны название, условие и хотя бы один шаг"}
    if len(steps) > MAX_STEPS:
        return {"ok": False, "error": f"у навыка может быть не больше {MAX_STEPS} шагов"}

    entries = [skill for skill in load(player_id) if skill.get("название") != name]
    entries.append({
        "название": name,
        "условие": trigger,
        "шаги": steps,
        "почему": rationale,
    })
    _write(player_id, entries)
    return {"ok": True, "навык": entries[-1], "всего_навыков": len(entries[-MAX_SKILLS:])}


def as_text(player_id: int) -> str:
    entries = load(player_id)
    if not entries:
        return "Навыков пока нет. Сохраняй только проверенные и повторяемые последовательности."
    lines = []
    for index, skill in enumerate(entries):
        steps = " → ".join(skill.get("шаги") or [])
        lines.append(
            f"[{index}] {skill.get('название', '')}: если {skill.get('условие', '')}; "
            f"делай {steps}. {skill.get('почему', '')}".strip()
        )
    return "\n".join(lines)


def forget(player_id: int, index: int) -> dict[str, Any]:
    entries = load(player_id)
    if not 0 <= index < len(entries):
        return {"ok": False, "error": f"нет навыка с номером {index}, всего {len(entries)}"}
    removed = entries.pop(index)
    _write(player_id, entries)
    return {"ok": True, "удалено": removed.get("название"), "осталось": len(entries)}
