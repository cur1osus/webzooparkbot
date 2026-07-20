"""The rival's own notebook: a JSON file per bot that it writes itself.

Not the operator's knowledge base — a bot's "the mountain locality never paid for itself"
belongs to the bot, not to anyone else's notes.

The point is that the *model* decides what goes in. A log written by the harness records
what happened; a note the bot chose to keep records what it thought was worth remembering,
and that difference is what makes the next turn read like the same player continuing rather
than a fresh one arriving. Reflection over transcript, as in Generative Agents.

Bounded on purpose: notes are what survives compaction of the raw history, so an unbounded
file would just recreate the transcript problem one level up. Oldest go first when full.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Overridable so a test (or a second deployment) never writes into the live bots' notes.
MEMORY_DIR = Path(os.getenv("BOT_MEMORY_DIR", "/opt/webzooparkbot/bot_memory"))

MAX_NOTES = 40
MAX_NOTE_CHARS = 400


def _path(player_id: int) -> Path:
    return MEMORY_DIR / f"bot_{player_id}.json"


def load(player_id: int) -> list[dict]:
    path = _path(player_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # A corrupt notebook must not stop a rival from playing; it starts a new one.
        logger.warning("bot %s has an unreadable memory file, starting empty", player_id)
        return []
    return data if isinstance(data, list) else []


def _save(player_id: int, notes: list[dict]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(player_id)
    # Write-then-rename: a crash mid-write leaves the previous notes intact rather than a
    # truncated file the next load would discard.
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=path.name, suffix=".tmp", delete=False
    ) as handle:
        json.dump(notes, handle, ensure_ascii=False, indent=1)
        temp = Path(handle.name)
    temp.replace(path)


def remember(player_id: int, note: str) -> dict:
    text = (note or "").strip()[:MAX_NOTE_CHARS]
    if not text:
        return {"ok": False, "error": "пустая заметка"}

    notes = load(player_id)
    notes.append({"когда": datetime.now(timezone.utc).strftime("%d.%m %H:%M"), "заметка": text})
    dropped = 0
    if len(notes) > MAX_NOTES:
        dropped = len(notes) - MAX_NOTES
        notes = notes[-MAX_NOTES:]
    _save(player_id, notes)
    return {"ok": True, "всего_заметок": len(notes), "вытеснено_старых": dropped}


def overwrite(player_id: int, notes: list[dict]) -> None:
    """Replace the whole notebook. Used by the dream pass, which distils many raw notes into
    a few durable ones; `remember` only ever appends."""
    _save(player_id, notes[-MAX_NOTES:])


def snapshot(player_id: int) -> Path | None:
    """Copy the current notebook aside before the dream rewrites it, so a bad consolidation
    can be read back and, if ever needed, restored. Overwritten each dream — one level of
    undo is enough; the point is provenance, not history."""
    notes = load(player_id)
    if not notes:
        return None
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    backup = MEMORY_DIR / f"bot_{player_id}.pre-dream.json"
    backup.write_text(json.dumps(notes, ensure_ascii=False, indent=1), encoding="utf-8")
    return backup


def make_note(text: str) -> dict:
    return {"когда": datetime.now(timezone.utc).strftime("%d.%m %H:%M"), "заметка": text[:MAX_NOTE_CHARS]}


def forget(player_id: int, index: int) -> dict:
    notes = load(player_id)
    if not 0 <= index < len(notes):
        return {"ok": False, "error": f"нет заметки с номером {index}, всего {len(notes)}"}
    removed = notes.pop(index)
    _save(player_id, notes)
    return {"ok": True, "удалено": removed.get("заметка"), "осталось": len(notes)}


def as_text(player_id: int) -> str:
    notes = load(player_id)
    if not notes:
        return "Заметок пока нет."
    return "\n".join(f"[{i}] {n.get('когда', '')} — {n.get('заметка', '')}" for i, n in enumerate(notes))
