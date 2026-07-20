"""The turn: the model looks around, decides, and pulls levers until it is done.

The model drives. There is no plan object and no hardcoded recipe — it calls `get_me`,
reads what came back, and decides what to do next from that. Everything it can do is in
`tools.REGISTRY`, and every entry there goes through the same service a human's request
goes through.

## The budget, and why it is counted in rounds

Cost is *rounds*, not tool calls. A round is one request to the model, and it resends the
whole conversation; the tool calls themselves are local Python and free. The model batches
heavily — in testing it asked for ten read tools in a single response — so counting tool
calls would have punished exactly the behaviour that is cheapest for us.

So `MAX_ROUNDS` is the real lever. `MAX_TOOL_CALLS` is only a runaway guard, and the
wall-clock deadline only catches a wedged network.

## Nothing is ever cut off mid-move

The budget is checked at the top of a round, before asking for more. An in-flight request
is never aborted and a running tool is never interrupted — if a deadline fired between
issuing a `breed` and recording its result, the game would have bred the animals while the
bot believed it had not, and the next turn would face a state it could not explain.

The model is also *told* its remaining budget, and warned as it runs low, so it winds down
on its own instead of being guillotined mid-thought.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from api.app.core.config import BOT_PLANNER_MODEL, ROUTERAI_API_KEY, ROUTERAI_BASE_URL
from api.bots import memory_store, tools
from api.bots.characters import Character

logger = logging.getLogger(__name__)

MAX_ROUNDS = 12
MAX_TOOL_CALLS = 40
DEADLINE_SECONDS = 600
REQUEST_TIMEOUT = 240
ATTEMPTS = 3
MAX_TOKENS = 3000

# ₽ per token on RouterAI, GET /api/v1/models, 2026-07-19. Cached input is ~5x cheaper,
# and the tool schemas are a stable ~6k-token prefix, so nearly all of it caches after the
# first round of a turn.
PRICE_PROMPT_RUB = 9.1726479e-06
PRICE_CACHED_RUB = 1.83452958e-06
PRICE_COMPLETION_RUB = 1.83452958e-05


SYSTEM_PROMPT = """Ты — игрок в браузерной игре про зоопарк, соперник живых людей. Ты не ассистент и не помощник: у тебя свой зоопарк, свои деньги и своя манера играть. Никто не даёт тебе заданий — ты сам решаешь, что делать.

Тебе доступны те же действия, что и любому игроку, и ровно через те же правила: цены, задержки и проверки одинаковы для всех. Если действие не прошло — тебе вернётся причина отказа, прочитай её и попробуй иначе.

Как устроена игра:
- Доход дают звери. С них же берётся содержание, и оно растёт с числом зверей. Если содержание догоняет доход — ты в минусе.
- Доход зверя зависит от генов: выживаемость, внешность, размер. Между худшим и лучшим — примерно восьмикратная разница.
- Локация не ограничивает число зверей. Её уровень снижает содержание, а зверь в локации своей среды обитания даёт x1.5 дохода. Зверь не в своей среде — тихая потеря.
- Звери смертны: слабая выживаемость около 4 дней, сильная около 15. Зоопарк надо обновлять.
- Больные звери приносят вдвое меньше и заражают соседей.
- Разведение даёт шанс на гены лучше родительских, но чаще выходит хуже. Нужны двое одного вида.
- Экспедиции приносят добычу и предметы, но звери возвращаются больными или не возвращаются вовсе. Глубже — больше и того, и другого.
- Паки — лотерея. Торговец дороже не всегда, зато зверь известен заранее.
- Кузница, кланы, дуэли и соло-игры — отдельные способы разогнать доход или спустить его.
- Сейф банка копит комиссии со всех обменов и открывается на четыре часа каждый вечер. В нём один код из четырёх цифр, он живёт, пока его не вскроют. Твои догадки запечатаны: подсказку ты получишь не сразу, а после закрытия окна — вместе со всеми. Зато вскрытые догадки всех игроков лежат на общей доске, и по ним код вычисляется. Угадаешь — заберёшь половину сейфа.

Как вести ход:
1. Сначала осмотрись. Можешь запросить несколько инструментов сразу одним ответом — это быстрее и дешевле, чем по одному.
2. Реши, что делаешь, и делай.
3. Если узнал что-то, чего не узнаешь заново — запиши заметку через remember. Блокнот маленький, и место в нём стоит тратить на выводы, а не на состояние: баланс, доход и цены ты в любой момент запросишь инструментом, а вот «экспедиция глубины 3 выкосила отряд» больше ниоткуда не всплывёт. Одна заметка за ход, и только если есть что записать.
4. Закончи ход через end_turn, когда сделал что хотел. Не обязательно тратить весь лимит.

Ты играешь вдолгую и ходишь регулярно. Не пытайся сделать всё за один ход."""


@dataclass
class TurnResult:
    rounds: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    summary: str = ""
    stopped_because: str = ""
    prompt_tokens: int = 0
    cached_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def cost_micro_rub(self) -> int:
        fresh = max(self.prompt_tokens - self.cached_tokens, 0)
        rub = (
            fresh * PRICE_PROMPT_RUB
            + self.cached_tokens * PRICE_CACHED_RUB
            + self.completion_tokens * PRICE_COMPLETION_RUB
        )
        return round(rub * 1_000_000)

    @property
    def actions(self) -> list[dict]:
        """Only the calls that changed something — what a human would call "what it did"."""
        return [c for c in self.tool_calls if c["name"] not in _READ_ONLY]


_READ_ONLY = {
    name for name in tools.REGISTRY
    if name.startswith(("get_", "list_", "read_")) or name in {"packs_info", "merchant_animals",
                                                                "forge_items", "forge_sets",
                                                                "clan_list", "clan_details",
                                                                "clan_members", "solo_stats",
                                                                "cocktail_state", "my_transfers",
                                                                "safe_state"}
}


def _post(payload: dict) -> dict:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(  # noqa: S310 — fixed https host from config
        f"{ROUTERAI_BASE_URL}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {ROUTERAI_API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:  # noqa: S310
        return json.loads(response.read())


def _ask(payload: dict) -> dict | None:
    """One round trip, retried on transport failure. Returns None when unreachable."""
    for attempt in range(ATTEMPTS):
        try:
            return _post(payload)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            if attempt == ATTEMPTS - 1:
                logger.warning("model unreachable after %s attempts: %s", ATTEMPTS, exc)
                return None
            time.sleep(3 * (attempt + 1))
    return None


def _opening_message(character: Character, player_id: int, nickname: str) -> str:
    return (
        f"Тебя зовут {nickname}.\n\n"
        f"{character.temperament}\n\n"
        f"ТВОИ ЗАМЕТКИ С ПРОШЛЫХ ХОДОВ:\n{memory_store.as_text(player_id)}\n\n"
        f"Начинается твой ход. У тебя {MAX_ROUNDS} обращений ко мне — "
        f"в каждом можешь запросить сразу несколько инструментов. Осмотрись и играй."
    )


def run_turn(character: Character, tg_id: int, player_id: int, nickname: str,
             *, dry_run: bool = False) -> TurnResult:
    """Play one turn. Never raises: a broken turn must not take down the runner.

    Under `dry_run` the model plays for real and its reasoning is genuine, but any tool that
    would change something is refused instead of executed — so you see what a rival intends
    without it spending a rouble. The refusal is reported to the model as an ordinary error,
    which does mean it will try to work around it; read a dry run for intent, not for the
    sequence it would have played uninterrupted.
    """
    result = TurnResult()

    if not ROUTERAI_API_KEY:
        result.stopped_because = "нет ROUTERAI_API_KEY"
        logger.warning("ROUTERAI_API_KEY is not set; rivals cannot play")
        return result

    # Built once for the turn: a state-gated tool (finish_expedition) is shown only if it
    # would do something now, and expeditions run for hours, so its availability cannot flip
    # mid-turn. Rebuilding every round would just re-query for no change.
    schemas = tools.schemas(tg_id, player_id)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _opening_message(character, player_id, nickname)},
    ]
    started = time.monotonic()

    while True:
        # Budget is checked here, before asking for more — never in the middle of a call.
        if result.rounds >= MAX_ROUNDS:
            result.stopped_because = "исчерпан лимит обращений"
            break
        if len(result.tool_calls) >= MAX_TOOL_CALLS:
            result.stopped_because = "исчерпан лимит вызовов"
            break
        if time.monotonic() - started > DEADLINE_SECONDS:
            result.stopped_because = "вышло время на ход"
            break

        remaining = MAX_ROUNDS - result.rounds
        if remaining <= 2:
            # Told, not cut off: it wraps up its own turn instead of stopping mid-thought.
            messages.append({
                "role": "user",
                "content": f"У тебя осталось {remaining} обращений. Заканчивай ход: "
                           f"сделай последнее важное, при желании запиши заметку и вызови end_turn.",
            })

        data = _ask({
            "model": BOT_PLANNER_MODEL,
            "messages": messages,
            "tools": schemas,
            "tool_choice": "auto",
            "max_tokens": MAX_TOKENS,
            "temperature": 1.0,
        })
        if data is None:
            result.stopped_because = "модель недоступна"
            break

        result.rounds += 1
        usage = data.get("usage") or {}
        details = usage.get("prompt_tokens_details") or {}
        completion_details = usage.get("completion_tokens_details") or {}
        result.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        result.cached_tokens += int(details.get("cached_tokens") or 0)
        result.completion_tokens += int(usage.get("completion_tokens") or 0)
        result.reasoning_tokens += int(completion_details.get("reasoning_tokens") or 0)

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            result.stopped_because = "неожиданный ответ модели"
            break

        calls = message.get("tool_calls") or []
        # The assistant turn must go back verbatim, tool_calls included, or the model loses
        # track of which results answer which request.
        messages.append({
            "role": "assistant",
            "content": message.get("content") or "",
            **({"tool_calls": calls} if calls else {}),
        })

        if not calls:
            # Talked instead of acting. Nudge once, then let the budget end it.
            result.summary = (message.get("content") or "").strip()[:500]
            messages.append({
                "role": "user",
                "content": "Ты ничего не сделал. Действуй инструментами или вызови end_turn.",
            })
            continue

        finished = False
        for entry in calls:
            function = entry.get("function") or {}
            name = function.get("name") or ""
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}

            if dry_run and name not in _READ_ONLY and name != "end_turn":
                output = {"ok": False, "error": "пробный прогон: изменяющие действия отключены"}
            else:
                output = tools.call(name, tg_id, player_id, arguments)
            result.tool_calls.append({"name": name, "аргументы": arguments, "результат": output})
            messages.append({
                "role": "tool",
                "tool_call_id": entry.get("id"),
                "content": json.dumps(output, ensure_ascii=False, default=str)[:4000],
            })
            if name == "end_turn":
                result.summary = str(arguments.get("summary") or "")[:500]
                result.stopped_because = "закончил сам"
                finished = True

        if finished:
            break

    logger.info(
        "bot %s: ход окончен (%s), кругов %s, действий %s, %.4f ₽",
        nickname, result.stopped_because, result.rounds, len(result.actions),
        result.cost_micro_rub / 1e6,
    )
    return result
