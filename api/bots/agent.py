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
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from api.app.core.config import (
    BOT_PLANNER_FALLBACK_MODEL,
    BOT_PLANNER_MODEL,
    ROUTERAI_API_KEY,
    ROUTERAI_BASE_URL,
)
from api.bots import audit, evaluator, memory_store, skills, tools
from api.bots.characters import Character

logger = logging.getLogger(__name__)

MAX_ROUNDS = 12
MAX_TOOL_CALLS = 40
DEADLINE_SECONDS = 600
REQUEST_TIMEOUT = 240
ATTEMPTS = 3
RESPONSE_ATTEMPTS = 3
RESPONSE_RETRY_DELAY_SECONDS = 1
FALLBACK_RESERVE_SECONDS = 120

_REQUEST_DEADLINE: ContextVar[float | None] = ContextVar("bot_request_deadline", default=None)

# ₽ per token on the configured model provider — (fresh input, output) per model.
# A turn resends its whole history every round, so input dominates: a measured turn is 278k
# in against 9k out. Which is also why the cache matters more than the sticker price — three
# quarters of that input is a repeat, and a model the router does not cache for costs roughly
# double its row here.
#
# The router publishes no rate for cached input; the fifth below is the ratio measured against
# deepseek-v4-flash's own invoices and assumed to carry. It is an assumption, and a new engine
# is worth re-checking against a real bill before its costs are compared to anyone else's.
CACHED_SHARE = 0.2
PRICES_RUB: dict[str, tuple[float, float]] = {
    "nvidia/nemotron-3-ultra-550b-a55b:free": (0.0, 0.0),
    "poolside/laguna-xs-2.1:free": (0.0, 0.0),
    "deepseek/deepseek-v4-flash": (9.1726479e-06, 1.83452958e-05),
    "z-ai/glm-4.7-flash": (6.1084319e-06, 4.0722879e-05),
}
FALLBACK_PRICE_MODEL = "deepseek/deepseek-v4-flash"


def _prices(model: str) -> tuple[float, float]:
    """Rates for `model`, or the incumbent's if it is one we have not priced yet.

    Guessing is the wrong failure here — an unpriced engine would silently be billed at
    DeepSeek's rates and then reported as cheaper or dearer than it is, which is exactly the
    comparison this column was added to make. So it says so, loudly, once per turn.
    """
    known = PRICES_RUB.get(model)
    if known is None:
        logger.warning("нет цены для модели %s — считаю по %s, цифры сравнивать нельзя",
                       model, BOT_PLANNER_MODEL)
        return PRICES_RUB[FALLBACK_PRICE_MODEL]
    return known


SYSTEM_PROMPT = """Ты — игрок в браузерной игре про зоопарк, соперник живых людей. Ты не ассистент и не помощник: у тебя свой зоопарк, свои деньги и своя манера играть. Никто не даёт тебе заданий — ты сам решаешь, что делать.

Тебе доступны те же действия, что и любому игроку, и ровно через те же правила: цены, задержки и проверки одинаковы для всех. Snapshot и результаты инструментов — источник истины для текущих чисел и правил; если этот текст, заметка или прежнее воспоминание расходятся с ними, верь свежему результату инструмента.

Как устроена игра:
- Доход дают звери. С них же берётся содержание, и оно растёт с числом зверей. Если содержание догоняет доход — ты в минусе.
- Доход зверя зависит от его характеристик, а выживаемость определяет риск будущей потери дохода. Смотри реальные значения в snapshot и list_animals.
- Локация влияет на доход и содержание. Своя среда обычно выгоднее чужой, а без локации зверь может не приносить доход вовсе. Сверяй фактический доход, содержание, среду и свободные локации перед покупкой.
- Звери смертны и могут заболеть. Snapshot показывает ближайшие смерти и болезни; оцени стоимость лечения, замены, разведения и потери дохода.
- Разведение даёт случайный результат и требует подходящей пары. Экспедиции дают добычу и предметы, но несут риск для отправленных зверей; сравнивай глубину с текущей потребностью.
- Паки — лотерея. Торговец дороже не всегда, зато зверь известен заранее.
- Кузница создаёт предметы с постоянными бонусами к доходу, содержанию, скидкам, банку или экспедициям. Кузница и паки — конкурирующие инвестиции: snapshot даёт цены партий и доступность предмета, но обязательного приоритета нет. Сравни текущий бонус, цену, темп дохода и риск лотереи сам; если паки выгоднее сейчас, покупай паки.
- Кузница и кланы — отдельные способы разогнать доход или спустить его.
- Сейф банка копит комиссии со всех обменов и открывается в определённое окно. Его состояние, срок, длину кода и число попыток смотри через safe_state; не запоминай эти значения как постоянные.
- У тебя есть лапки (paw) — их платят за коктейль и достижения, и копятся они без дела. Трать их на внешность: цвет ника, рамку, обои, тему, аватар из открытого достижения (my_achievements покажет открытые). На доход это не влияет, но профиль видят соперники в топе — будь креативным, собери себе облик, который не спутать с дефолтным. Что доступно и почём — в get_me.

Как вести ход:
1. Начни со свежего компактного снимка и первым содержательным действием вызови set_turn_goal: запиши одну цель, ожидаемый наблюдаемый эффект и главную альтернативу. Не фиксируй цель как приказ — после проверки можешь её пересмотреть.
2. Если snapshot говорит, что звери скоро умрут или больны, включи стоимость этой угрозы в сравнение. Не открывай лотерею вслепую.
3. Делай одну-две изменяющие операции и используй автоматическую проверку состояния. Если цель требует продолжения, продолжай после проверки; это рекомендация к коротким итерациям, а не жёсткий лимит.
4. Подробные list_* и get_* вызывай только для уточнения перед конкретным действием — snapshot уже содержит разведку первого уровня.
5. После каждой проверки сравни ожидаемый эффект с фактическим: что изменилось, достигнута ли цель и что делать дальше.
6. Если проверенный вывод пригодится снова, запиши его через remember. Если успешная последовательность повторяема, сохрани её через save_skill с условием и шагами. Не записывай баланс и текущие цены.
7. Заверши ход через end_turn, указав goal_reached, observed_result и next_adjustment. Не обязательно тратить весь лимит.

Ты играешь вдолгую и ходишь регулярно. Не пытайся сделать всё за один ход."""


@dataclass
class TurnResult:
    rounds: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    summary: str = ""
    stopped_because: str = ""
    model: str = BOT_PLANNER_MODEL
    prompt_tokens: int = 0
    cached_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    goal: dict = field(default_factory=dict)
    reflection: dict = field(default_factory=dict)
    evaluation: dict = field(default_factory=dict)
    initial_snapshot: dict = field(default_factory=dict)
    final_snapshot: dict = field(default_factory=dict)

    @property
    def cost_micro_rub(self) -> int:
        prompt_rub, completion_rub = _prices(self.model)
        fresh = max(self.prompt_tokens - self.cached_tokens, 0)
        rub = (
            fresh * prompt_rub
            + self.cached_tokens * prompt_rub * CACHED_SHARE
            + self.completion_tokens * completion_rub
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
                                                                "clan_members",
                                                                "cocktail_state", "my_transfers",
                                                                "safe_state"}
}
_READ_ONLY |= {"set_turn_goal", "save_skill", "forget_skill"}

# The only tools left on the table for the final round: write the lesson down, then close.
_CLOSING = {"remember", "save_skill", "end_turn"}


def _post(payload: dict) -> dict:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(  # noqa: S310 — fixed https host from config
        f"{ROUTERAI_BASE_URL}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {ROUTERAI_API_KEY}", "Content-Type": "application/json"},
    )
    deadline = _REQUEST_DEADLINE.get()
    timeout = REQUEST_TIMEOUT
    if deadline is not None:
        timeout = max(min(REQUEST_TIMEOUT, deadline - time.monotonic()), 1.0)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read())


def _ask(payload: dict) -> dict | None:
    """One round trip, retried on transport failure. Returns None when unreachable."""
    for attempt in range(ATTEMPTS):
        deadline = _REQUEST_DEADLINE.get()
        if deadline is not None and time.monotonic() >= deadline:
            logger.warning("модель не успела ответить до резервного дедлайна")
            return None
        try:
            return _post(payload)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            if attempt == ATTEMPTS - 1:
                logger.warning("model unreachable after %s attempts: %s", ATTEMPTS, exc)
                return None
            delay = float(3 * (attempt + 1))
            if deadline is not None:
                delay = min(delay, max(deadline - time.monotonic(), 0.0))
            if delay > 0:
                time.sleep(delay)
    return None


def _normalize_chat_response(data: dict | None) -> dict | None:
    """Accept the normal Chat Completions shape and harmless provider variants."""
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        return data
    if isinstance(choices, dict):
        return {**data, "choices": [choices]}
    message = data.get("message")
    if isinstance(message, dict):
        return {**data, "choices": [{"message": message, "finish_reason": data.get("finish_reason")}]}
    if "tool_calls" in data or "content" in data:
        return {
            **data,
            "choices": [{
                "message": {
                    "content": data.get("content") or "",
                    "tool_calls": data.get("tool_calls") or [],
                },
                "finish_reason": data.get("finish_reason"),
            }],
        }
    return None


def _response_is_usable(data: dict | None) -> bool:
    """Whether the provider response has the message shape the turn loop can consume."""
    normalized = _normalize_chat_response(data)
    if normalized is None:
        return False
    try:
        choice = normalized["choices"][0]
    except (KeyError, IndexError, TypeError):
        return False
    if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
        return False
    calls = choice["message"].get("tool_calls") or []
    return isinstance(calls, list) and all(isinstance(call, dict) for call in calls)


def _ask_with_response_retries(
    payload: dict, *, deadline: float | None = None,
) -> tuple[dict | None, bool]:
    """Retry malformed provider payloads without replaying any game tool.

    The retry happens before the round is recorded and before the assistant message is added
    to the conversation. Therefore a successful retry is indistinguishable from a transient
    provider glitch and can never execute an already-executed mutating call twice.
    """
    token = _REQUEST_DEADLINE.set(deadline)
    try:
        for attempt in range(RESPONSE_ATTEMPTS):
            raw_data = _ask(payload)
            if raw_data is None:
                return None, False
            if _response_is_usable(raw_data):
                return raw_data, False
            logger.warning(
                "ответ модели неполный или имеет неизвестную форму, повтор %s/%s, id=%r keys=%s",
                attempt + 1, RESPONSE_ATTEMPTS, raw_data.get("id"), sorted(raw_data.keys()),
            )
            if attempt < RESPONSE_ATTEMPTS - 1 and RESPONSE_RETRY_DELAY_SECONDS > 0:
                delay = float(RESPONSE_RETRY_DELAY_SECONDS)
                if deadline is not None:
                    delay = min(delay, max(deadline - time.monotonic(), 0.0))
                if delay > 0:
                    time.sleep(delay)
        return None, True
    finally:
        _REQUEST_DEADLINE.reset(token)


def _fallback_model_for(model: str) -> str | None:
    """Return a distinct free engine for a failed round, if one is configured."""
    if BOT_PLANNER_FALLBACK_MODEL and BOT_PLANNER_FALLBACK_MODEL != model:
        return BOT_PLANNER_FALLBACK_MODEL
    return None


def _opening_message(character: Character, tg_id: int, player_id: int, nickname: str,
                     snapshot: dict | None = None) -> str:
    # The auditor's block comes after the notes and says so: the notebook is what the rival
    # remembers, and it has been wrong. See `audit.py`.
    review = audit.as_text(tg_id)
    snapshot_text = ""
    if snapshot:
        snapshot_text = (
            "СВЕЖИЙ СНИМОК СОСТОЯНИЯ (это факты для выбора цели; за деталями зови инструменты):\n"
            + json.dumps(snapshot, ensure_ascii=False, default=str, separators=(",", ":"))
            + "\n\n"
        )
    skill_text = skills.as_text(player_id)
    return (
        f"Тебя зовут {nickname}.\n\n"
        f"{character.temperament}\n\n"
        f"ТВОИ ЗАМЕТКИ С ПРОШЛЫХ ХОДОВ:\n{memory_store.as_text(player_id)}\n\n"
        f"БИБЛИОТЕКА ПРОВЕРЕННЫХ НАВЫКОВ:\n{skill_text}\n\n"
        + snapshot_text
        + (f"{review}\n\n" if review else "")
        + f"Начинается твой ход. У тебя {MAX_ROUNDS} обращений ко мне — "
        f"в каждом можешь запросить сразу несколько инструментов. Осмотрись и играй."
    )


def run_turn(character: Character, tg_id: int, player_id: int, nickname: str,
             *, dry_run: bool = False, model: str | None = None) -> TurnResult:
    """Play one turn. Never raises: a broken turn must not take down the runner.

    Under `dry_run` the model plays for real and its reasoning is genuine, but any tool that
    would change something is refused instead of executed — so you see what a rival intends
    without it spending a rouble. The refusal is reported to the model as an ordinary error,
    which does mean it will try to work around it; read a dry run for intent, not for the
    sequence it would have played uninterrupted.
    """
    result = TurnResult(model=model or BOT_PLANNER_MODEL)

    if not ROUTERAI_API_KEY:
        result.stopped_because = "нет ROUTERAI_API_KEY"
        logger.warning("ROUTERAI_API_KEY is not set; rivals cannot play")
        return result

    # Built once for the turn: a state-gated tool (finish_expedition) is shown only if it
    # would do something now, and expeditions run for hours, so its availability cannot flip
    # mid-turn. Rebuilding every round would just re-query for no change.
    schemas = tools.schemas(tg_id, player_id)
    initial_snapshot = tools.call("get_turn_snapshot", tg_id, player_id, {})
    result.initial_snapshot = initial_snapshot
    result.tool_calls.append({
        "name": "get_turn_snapshot",
        "аргументы": {},
        "результат": initial_snapshot,
    })
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _opening_message(
            character, tg_id, player_id, nickname, initial_snapshot,
        )},
    ]
    started = time.monotonic()
    turn_deadline = started + DEADLINE_SECONDS
    primary_deadline = max(started, turn_deadline - FALLBACK_RESERVE_SECONDS)
    fallback_used = False

    while True:
        # Budget is checked here, before asking for more — never in the middle of a call.
        if result.rounds >= MAX_ROUNDS:
            result.stopped_because = "исчерпан лимит обращений"
            break
        model_tool_calls = sum(
            call.get("name") != "get_turn_snapshot" for call in result.tool_calls
        )
        if model_tool_calls >= MAX_TOOL_CALLS:
            result.stopped_because = "исчерпан лимит вызовов"
            break
        if time.monotonic() - started > DEADLINE_SECONDS:
            result.stopped_because = "вышло время на ход"
            break

        # The last two rounds are reserved for closing the turn, and each is narrowed further
        # than the one before. Asking in words was not enough — over half the turns spent the
        # warning rounds on more tool calls and hit the ceiling with neither a note nor a
        # summary. Hiding the other tools was not enough either: handed only `remember` and
        # `end_turn`, the model answered one round with no tool call and no text at all, and
        # the turn still ended with nothing recorded. So the last round does not ask.
        remaining = MAX_ROUNDS - result.rounds
        round_schemas = schemas
        tool_choice: Any = "auto"
        if remaining == 2:
            # A round to write the lesson down, with nothing else on the table to spend it on.
            round_schemas = [s for s in schemas if s["function"]["name"] in _CLOSING]
            messages.append({
                "role": "user",
                "content": "Осталось 2 обращения. Если есть повторяемая успешная "
                           "последовательность, сохрани её через save_skill; затем вызови "
                           "end_turn с оценкой цели и наблюдаемым результатом.",
            })
        elif remaining <= 1:
            # And a round that can only be `end_turn`, so a turn always leaves a summary.
            round_schemas = [s for s in schemas if s["function"]["name"] == "end_turn"]
            tool_choice = {"type": "function", "function": {"name": "end_turn"}}
            messages.append({
                "role": "user",
                "content": "Последнее обращение. Вызови end_turn с итогом хода.",
            })

        payload = {
            "model": result.model,
            "messages": messages,
            "tools": round_schemas,
            "tool_choice": tool_choice,
            "temperature": 1.0,
        }
        # Do not impose a local output-token ceiling. OpenRouter/model defaults decide the
        # response size; the agent-level rounds, tool-call and wall-clock guards remain the
        # actual runaway protection.
        request_deadline = turn_deadline if fallback_used else primary_deadline
        raw_data, invalid_response = _ask_with_response_retries(
            payload, deadline=request_deadline,
        )
        if raw_data is None:
            fallback_model = _fallback_model_for(result.model)
            if fallback_model:
                logger.warning(
                    "bot %s: модель %s не ответила после %s попыток; переключаюсь на %s",
                    nickname, result.model, RESPONSE_ATTEMPTS, fallback_model,
                )
                result.model = fallback_model
                fallback_used = True
                payload["model"] = fallback_model
                raw_data, invalid_response = _ask_with_response_retries(
                    payload, deadline=turn_deadline,
                )
        if raw_data is None:
            result.stopped_because = (
                "неожиданный ответ модели" if invalid_response else "модель недоступна"
            )
            break
        data = _normalize_chat_response(raw_data)
        if data is None:
            logger.warning(
                "bot %s: ответ модели без распознаваемого choices, id=%r keys=%s error=%r",
                nickname, raw_data.get("id"), sorted(raw_data.keys()), raw_data.get("error"),
            )
            result.stopped_because = "неожиданный ответ модели"
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
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError):
            result.stopped_because = "неожиданный ответ модели"
            break

        # `length` means the provider cut off whatever it was emitting — including, possibly,
        # a tool call's arguments mid-string. We still process the calls that parsed; the
        # truncated one is caught below and turned into an error, never run.
        truncated = choice.get("finish_reason") == "length"
        if truncated:
            logger.warning("bot %s: провайдер обрезал ответ по длине", nickname)

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
        changed_state = False
        for entry in calls:
            function = entry.get("function") or {}
            name = function.get("name") or ""
            raw_arguments = function.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_arguments)
                if not isinstance(arguments, dict):
                    raise json.JSONDecodeError("не объект", raw_arguments, 0)
                malformed = False
            except json.JSONDecodeError:
                arguments, malformed = {}, True

            if malformed:
                # The arguments did not parse — almost always because the round was truncated
                # mid-call. Substituting {} and running it anyway once let a no-argument
                # mutating tool (cure_all_animals, clan_leave, reroll_daily_bonus) fire on a
                # fragment the model never finished asking for. Refuse it instead; the model
                # sees the error and reissues the call whole. A tool is never run on a guess.
                output = {"ok": False, "error": "аргументы не разобрались — ответ, похоже, "
                                                "обрезан; повтори этот вызов целиком и короче"}
            elif dry_run and name not in _READ_ONLY and name != "end_turn":
                output = {"ok": False, "error": "пробный прогон: изменяющие действия отключены"}
            else:
                output = tools.call(name, tg_id, player_id, arguments)
            result.tool_calls.append({"name": name, "аргументы": arguments, "результат": output})
            if name not in _READ_ONLY and name not in {"end_turn", "remember", "forget"}:
                changed_state = True
            if name == "set_turn_goal" and not malformed and output.get("ok"):
                result.goal = {
                    "objective": arguments.get("objective", ""),
                    "expected_effect": arguments.get("expected_effect", ""),
                    "alternative": arguments.get("alternative", ""),
                }
            messages.append({
                "role": "tool",
                "tool_call_id": entry.get("id"),
                "content": json.dumps(output, ensure_ascii=False, default=str)[:4000],
            })
            # Only a cleanly-parsed end_turn ends the turn: a truncated one has no summary and
            # is not a real decision to stop.
            if name == "end_turn" and not malformed:
                result.summary = str(arguments.get("summary") or "")[:500]
                result.reflection = {
                    "goal_reached": arguments.get("goal_reached", "uncertain"),
                    "observed_result": str(arguments.get("observed_result") or "")[:500],
                    "next_adjustment": str(arguments.get("next_adjustment") or "")[:500],
                }
                result.stopped_because = "закончил сам"
                finished = True

        if finished:
            break

        if changed_state:
            verification = tools.call("get_turn_snapshot", tg_id, player_id, {})
            result.tool_calls.append({
                "name": "get_turn_snapshot",
                "аргументы": {"автоматическая_проверка": True},
                "результат": verification,
            })
            messages.append({
                "role": "user",
                "content": "АВТОПРОВЕРКА ПОСЛЕ ИЗМЕНЕНИЙ:\n"
                           + json.dumps(verification, ensure_ascii=False, default=str,
                                         separators=(",", ":"))
                           + "\nПересмотри цель, прежде чем делать следующий шаг.",
            })

        if truncated:
            # Told, so the next round comes back shorter instead of being cut off again.
            messages.append({
                "role": "user",
                "content": "Твой прошлый ответ обрезался по длине — отвечай короче, "
                           "по одному-двум шагам за раз.",
            })

    result.final_snapshot = evaluator.final_snapshot(result.tool_calls, result.initial_snapshot)
    result.evaluation = evaluator.evaluate(
        result.initial_snapshot,
        result.final_snapshot,
        result.tool_calls,
        rounds=result.rounds,
        stopped_because=result.stopped_because,
        model=result.model,
        goal=result.goal,
        reflection=result.reflection,
    )
    logger.info(
        "bot %s: ход окончен (%s), кругов %s, действий %s, %.4f ₽",
        nickname, result.stopped_because, result.rounds, len(result.actions),
        result.cost_micro_rub / 1e6,
    )
    return result
