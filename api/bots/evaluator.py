"""Small, deterministic outcome metrics for one rival turn.

The model's journal answers "what did it call?".  This module answers the cheaper and more
useful operator question: "did the state move in the right direction?".  It deliberately
does not judge whether a goal was completed — that would be pretending that a heuristic is a
ground-truth evaluator.  It records observable deltas and enough signals to compare turns,
models, and guardrail hits later.
"""

from __future__ import annotations

from typing import Any


_NON_ACTIONS = {
    "end_turn",
    "remember",
    "forget",
    "get_turn_snapshot",
}


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    return None


def _path(snapshot: dict[str, Any], *keys: str) -> int | float | None:
    value: Any = snapshot
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return _number(value)


def _delta(before: dict[str, Any], after: dict[str, Any], *keys: str) -> dict[str, Any]:
    old = _path(before, *keys)
    new = _path(after, *keys)
    result: dict[str, Any] = {"before": old, "after": new}
    if old is not None and new is not None:
        result["delta"] = new - old
    return result


def _margin(snapshot: dict[str, Any]) -> int | float | None:
    income = _path(snapshot, "игрок", "доход_руб_мин")
    upkeep = _path(snapshot, "игрок", "содержание_руб_мин")
    if income is None or upkeep is None:
        return None
    return income - upkeep


def _last_snapshot(tool_calls: list[dict[str, Any]], fallback: dict[str, Any]) -> dict[str, Any]:
    for call in reversed(tool_calls):
        if call.get("name") == "get_turn_snapshot" and isinstance(call.get("результат"), dict):
            return call["результат"]
    return fallback


def evaluate(
    initial: dict[str, Any],
    final: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    *,
    rounds: int,
    stopped_because: str,
    model: str,
    goal: dict[str, Any] | None = None,
    reflection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build JSON-safe, deliberately modest outcome metrics for a turn."""
    calls = [call for call in tool_calls if isinstance(call, dict)]
    outputs = [call.get("результат") for call in calls]
    successful_outputs = [output for output in outputs if isinstance(output, dict)]
    actions = [
        call for call in calls
        if call.get("name") not in _NON_ACTIONS
        and not str(call.get("name", "")).startswith(("get_", "list_", "read_"))
        and call.get("name") not in {
            "packs_info", "merchant_animals", "forge_items", "forge_sets", "clan_list",
            "clan_details", "clan_members", "cocktail_state", "my_transfers", "safe_state",
        }
    ]
    failed = [output for output in successful_outputs if output.get("ok") is False]
    packs = [call for call in calls if call.get("name") == "open_pack"]
    pack_quantity = sum(
        int((call.get("аргументы") or {}).get("quantity") or 1)
        for call in packs
        if isinstance(call.get("аргументы"), dict)
    )
    forge_names = {"forge_create", "forge_upgrade", "forge_activate", "forge_merge", "forge_set_apply"}
    large_packs = [
        call for call in packs
        if int((call.get("аргументы") or {}).get("quantity") or 1) in (50, 100)
    ]
    forge_state = initial.get("кузница") or {}
    forge_affordable = bool(
        forge_state.get("можно_создать_за_usd") or forge_state.get("можно_создать_за_лапки")
    )

    metrics: dict[str, Any] = {
        "schema_version": 1,
        "model": model,
        "rounds": rounds,
        "stopped_cleanly": stopped_because == "закончил сам",
        "stopped_because": stopped_because,
        "tool_call_count": len(calls),
        "action_count": len(actions),
        "failed_tool_calls": len(failed),
        "successful_tool_calls": len(successful_outputs) - len(failed),
        "pack_calls": len(packs),
        "pack_quantity_requested": pack_quantity,
        "forge_calls": sum(call.get("name") in forge_names for call in calls),
        "safe_calls": sum(call.get("name") == "safe_guess" for call in calls),
        "goal": goal or {},
        "goal_defined": bool(goal),
        "goal_reached": (reflection or {}).get("goal_reached", "uncertain"),
        "observed_result": (reflection or {}).get("observed_result", ""),
        "next_adjustment": (reflection or {}).get("next_adjustment", ""),
        "skills_saved": sum(call.get("name") == "save_skill" for call in calls),
        "forge_affordable_before_turn": forge_affordable,
        "large_pack_calls_with_forge_available": len(large_packs) if forge_affordable else 0,
        "snapshot_errors_before": initial.get("не_прочитано", []),
        "snapshot_errors_after": final.get("не_прочитано", []),
    }

    for label, path in {
        "rub": ("игрок", "рубли"),
        "usd": ("игрок", "доллары"),
        "paw": ("игрок", "лапки"),
        "income_rub_per_min": ("игрок", "доход_руб_мин"),
        "upkeep_rub_per_min": ("игрок", "содержание_руб_мин"),
        "animals": ("зоопарк", "зверей"),
        "sick_animals": ("зоопарк", "больных"),
        "unassigned_animals": ("зоопарк", "без_локации"),
        "misplaced_animals": ("зоопарк", "не_в_своей_среде"),
        "deaths_in_6h": ("зоопарк", "умирают_в_6ч"),
    }.items():
        metrics[label] = _delta(initial, final, *path)

    before_margin = _margin(initial)
    after_margin = _margin(final)
    metrics["income_margin_rub_per_min"] = {
        "before": before_margin,
        "after": after_margin,
        **({"delta": after_margin - before_margin}
           if before_margin is not None and after_margin is not None else {}),
    }
    metrics["last_snapshot_source"] = "turn_snapshot"
    return metrics


def final_snapshot(tool_calls: list[dict[str, Any]], initial: dict[str, Any]) -> dict[str, Any]:
    return _last_snapshot(tool_calls, initial)
