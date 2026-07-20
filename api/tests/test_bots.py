"""Invariants of the AI rivals that are cheap to break and expensive to notice.

Nothing here calls the model. What matters is the machinery around it: that every tool the
model can see is one it can actually call, that a bad call comes back as data instead of an
exception, and that the budget cannot be spent in a way that severs a move half-done.
"""

from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from api.bots import agent, memory_store, runner, tools
from api.bots.characters import CHARACTERS, get
from api.bots.runner import _awake, _journal


class _Profile:
    def __init__(self, wake: int, sleep: int) -> None:
        self.wake_hour_utc = wake
        self.sleep_hour_utc = sleep


# ── the toolset ───────────────────────────────────────────────────────────────


def test_every_tool_is_callable_and_declares_its_arguments():
    """A tool whose schema names a parameter its function does not accept fails only when
    the model happens to use it — possibly days later, in production."""
    import inspect

    for name, entry in tools.REGISTRY.items():
        assert entry.run is not None, f"{name} has no implementation"
        signature = inspect.signature(entry.run)
        accepts_kwargs = any(
            p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
        )
        for argument in entry.properties:
            assert argument in signature.parameters or accepts_kwargs, (
                f"{name} declares {argument!r} but its function cannot accept it"
            )
        for argument in entry.required:
            assert argument in entry.properties, f"{name} requires undeclared {argument!r}"


def test_schemas_are_wellformed_for_the_api():
    for schema in tools.schemas():
        function = schema["function"]
        assert schema["type"] == "function"
        assert function["name"] and function["description"]
        assert function["parameters"]["type"] == "object"


def test_the_squad_bounds_a_tool_advertises_are_the_ones_the_game_enforces():
    """`start_expedition` used to advertise "1-16 своих зверей" while the game enforced 3-5.
    The model cannot see the rule except by being refused, so a stale bound here costs it
    real calls every turn."""
    from api.app.zoopark.catalog import EXPEDITION_SQUAD_MAX, EXPEDITION_SQUAD_MIN

    animals = tools.REGISTRY["start_expedition"].properties["animal_ids"]
    assert animals["minItems"] == EXPEDITION_SQUAD_MIN
    assert animals["maxItems"] == EXPEDITION_SQUAD_MAX


def test_the_cocktail_tool_names_the_fruits_it_will_accept():
    """The fruits are emoji. Told only "fruits", the model guesses the words "ананас" and
    "лимон" and spends its whole turn on "Неизвестный фрукт"."""
    from api.app.zoopark.catalog import COCKTAIL_FRUITS, COCKTAIL_LENGTH

    entry = tools.REGISTRY["cocktail_guess"]
    assert set(entry.properties["fruits"]["items"]["enum"]) == set(COCKTAIL_FRUITS)
    assert entry.properties["fruits"]["minItems"] == COCKTAIL_LENGTH
    for fruit in COCKTAIL_FRUITS:
        assert fruit in entry.description, "палитра должна быть видна и в самом описании"


def test_end_turn_exists_so_a_rival_can_stop_early():
    """Without it the only way a turn ends is by exhausting the budget, which both costs
    money and reads as a bot that cannot tell when it is finished."""
    assert "end_turn" in tools.REGISTRY


def test_read_only_set_covers_no_mutating_tool():
    """`_READ_ONLY` gates the dry run. A mutating tool wrongly listed there would spend real
    money during what is supposed to be a look-but-don't-touch pass."""
    mutating = {
        "open_pack", "buy_locality", "upgrade_locality", "breed", "release_animal",
        "start_expedition", "create_duel", "join_duel", "create_transfer", "forge_create",
        "exchange_to_usd", "clan_create", "merchant_buy", "cure_all_animals", "safe_guess",
    }
    assert not (mutating & agent._READ_ONLY)


def test_reading_the_safe_is_not_mistaken_for_an_action():
    """`safe_state` matches none of the `get_`/`list_` prefixes, so without the explicit
    entry a dry run would refuse it and every turn would report a phantom action."""
    assert "safe_state" in agent._READ_ONLY


# ── dispatch ──────────────────────────────────────────────────────────────────


def test_unknown_tool_comes_back_as_data():
    result = tools.call("не_существует", tg_id=-1, player_id=1, arguments={})
    assert result["ok"] is False and "не_существует" in result["error"]


def test_a_refusal_from_the_game_is_reported_not_raised(monkeypatch):
    """`HTTPException` is how the services say "too poor" or "on cooldown". Letting it
    escape would end the turn over an ordinary no; the model should read it and adapt."""
    def refuse(**_):
        raise HTTPException(400, "Недостаточно средств")

    monkeypatch.setitem(tools.REGISTRY, "breed", tools.Tool("breed", "d", {}, [], refuse))
    result = tools.call("breed", tg_id=-1, player_id=1, arguments={})
    assert result == {"ok": False, "error": "Недостаточно средств"}


def test_a_crashing_tool_does_not_end_the_turn(monkeypatch):
    def explode(**_):
        raise RuntimeError("boom")

    monkeypatch.setitem(tools.REGISTRY, "breed", tools.Tool("breed", "d", {}, [], explode))
    result = tools.call("breed", tg_id=-1, player_id=1, arguments={})
    assert result["ok"] is False


def test_wrong_arguments_come_back_as_a_readable_error(monkeypatch):
    monkeypatch.setitem(
        tools.REGISTRY, "breed", tools.Tool("breed", "d", {}, [], lambda *, tg_id, player_id: None)
    )
    result = tools.call("breed", tg_id=-1, player_id=1, arguments={"нет_такого": 1})
    assert result["ok"] is False and "аргумент" in result["error"]


# ── budget ────────────────────────────────────────────────────────────────────


def test_the_budget_is_counted_in_rounds_not_tool_calls():
    """Rounds are what cost money — a round resends the whole conversation, while the tools
    are local calls. The model batches ten tools into one round, and capping tool calls
    would punish exactly that."""
    assert agent.MAX_ROUNDS < agent.MAX_TOOL_CALLS


def test_the_deadline_leaves_room_for_a_full_budget_of_rounds():
    """If the clock could fire before the rounds run out, the wall-clock backstop would
    become the real limit and turns would end unpredictably mid-thought."""
    assert agent.DEADLINE_SECONDS >= agent.MAX_ROUNDS * 20


def test_cost_prices_cached_input_below_fresh_input():
    result = agent.TurnResult(prompt_tokens=10_000, cached_tokens=10_000, completion_tokens=0)
    expensive = agent.TurnResult(prompt_tokens=10_000, cached_tokens=0, completion_tokens=0)
    assert 0 < result.cost_micro_rub < expensive.cost_micro_rub


def test_actions_exclude_reads():
    result = agent.TurnResult()
    result.tool_calls = [
        {"name": "get_me", "аргументы": {}, "результат": {"ok": True}},
        {"name": "breed", "аргументы": {}, "результат": {"ok": True}},
    ]
    assert [call["name"] for call in result.actions] == ["breed"]


# ── the journal ───────────────────────────────────────────────────────────────


def test_a_huge_turn_still_fits_the_journal_column():
    """MySQL's TEXT holds 64 KiB and a grown zoo serialises past it, which threw on insert
    and lost the row. SQLite is unbounded, so only production ever saw this."""
    fat = {"animals": [{"id": i, "name": "зверь", "genes": "x" * 200} for i in range(400)]}
    payload = _journal([{"name": "list_animals", "аргументы": {}, "результат": fat}] * 30)
    assert len(payload) <= runner.MAX_JOURNAL_CHARS + 1
    assert len(payload.encode("utf-8")) < 16 * 1024 * 1024, "должно влезать в MEDIUMTEXT"


def test_the_journal_keeps_what_a_review_needs():
    """Clipping is for the payloads, not the shape: which tool ran with which arguments is
    the whole point of reading the log a day later."""
    payload = _journal([{"name": "breed", "аргументы": {"a": 1}, "результат": {"ok": True}}])
    entry = json.loads(payload)[0]
    assert entry["name"] == "breed" and entry["аргументы"] == {"a": 1}
    assert "ok" in entry["результат"]


def test_a_clipped_result_says_that_it_was_clipped():
    payload = _journal([{"name": "list_animals", "аргументы": {}, "результат": {"x": "y" * 9000}}])
    assert "обрезано" in json.loads(payload)[0]["результат"]


def test_a_failed_journal_does_not_make_the_rival_take_the_turn_again(db, monkeypatch):
    """The journal insert and the schedule update once shared a transaction, so a failing
    insert rolled back `next_turn_at` too and the rival came back a minute later and paid
    for another turn. It ran that loop for half an hour at ~15x its intended spend."""
    from datetime import timedelta

    from sqlalchemy import select

    from api.app.db.connection import get_session
    from api.app.db.models import BotProfile, Player, utcnow
    from api.app.schemas.core import RegisterBody
    from api.app.zoopark.core import register

    register(-1002, RegisterBody(nickname="Сфорца"))
    with get_session() as session:
        player = session.scalar(select(Player).where(Player.telegram_id == -1002))
        player.is_bot = True
        player_id = player.id
        session.add(BotProfile(
            player_id=player_id, character="gambler", enabled=True, turn_every_minutes=45,
            wake_hour_utc=0, sleep_hour_utc=0, biography="", created_at=utcnow(),
        ))
        session.commit()

    monkeypatch.setattr(runner.agent, "run_turn", lambda *a, **k: agent.TurnResult(rounds=3))

    def explode(_):
        raise RuntimeError("Data too long for column 'tool_calls'")

    monkeypatch.setattr(runner, "_journal", explode)

    before = utcnow()
    assert runner._process(player_id, before, dry_run=False) is True

    with get_session() as session:
        profile = session.get(BotProfile, player_id)
        assert profile.next_turn_at is not None, "расписание не должно откатываться вместе с логом"
        assert profile.next_turn_at >= before + timedelta(minutes=44)


# ── characters and rhythm ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("wake", "sleep", "hour", "expected"),
    [
        (6, 22, 12, True),
        (6, 22, 3, False),
        (6, 22, 22, False),   # the sleep hour itself is off
        (11, 2, 23, True),    # window wrapping past midnight
        (11, 2, 1, True),
        (11, 2, 5, False),
        (0, 0, 13, True),     # wake == sleep means always awake
    ],
)
def test_waking_window(wake, sleep, hour, expected):
    assert _awake(_Profile(wake, sleep), hour) is expected


def test_characters_are_distinct_enough_to_tell_apart():
    names = [c.nickname for c in CHARACTERS.values()]
    assert len(names) == len(set(names))
    windows = [(c.wake_hour_utc, c.sleep_hour_utc) for c in CHARACTERS.values()]
    assert len(windows) == len(set(windows)), "ривалы с одинаковым расписанием читаются как один"


def test_a_character_never_carries_a_raw_avatar():
    """A rival's avatar must be earned like a player's. A glyph on the character would make
    the bots the only accounts rendering as a bare character instead of an animal or medal."""
    assert not any(hasattr(c, "emoji") for c in CHARACTERS.values())


def test_opening_message_carries_the_notes_and_the_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    memory_store.remember(1, "паки меня трижды подводили")
    message = agent._opening_message(get("gambler"), 1, "Рагнар")
    assert "Рагнар" in message
    assert "паки меня трижды подводили" in message
    assert str(agent.MAX_ROUNDS) in message


# ── memory ────────────────────────────────────────────────────────────────────


def test_memory_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    memory_store.remember(7, "горная локация не окупилась")
    assert "горная локация" in memory_store.as_text(7)
    assert memory_store.forget(7, 0)["ok"] is True
    assert memory_store.load(7) == []


def test_memory_is_bounded_so_it_cannot_become_a_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    for i in range(memory_store.MAX_NOTES + 15):
        memory_store.remember(9, f"заметка {i}")
    notes = memory_store.load(9)
    assert len(notes) == memory_store.MAX_NOTES
    assert notes[-1]["заметка"].endswith(str(memory_store.MAX_NOTES + 14))


def test_a_corrupt_notebook_does_not_stop_the_bot(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "bot_3.json").write_text("{ это не json", encoding="utf-8")
    assert memory_store.load(3) == []
    assert memory_store.remember(3, "новая")["ok"] is True


def test_forget_rejects_a_number_that_is_not_there(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    assert memory_store.forget(4, 99)["ok"] is False


# ── the safe ──────────────────────────────────────────────────────────────────


def test_a_rival_plays_the_safe_through_the_same_service_as_a_player(db, monkeypatch):
    """The rival must reach the safe by the player's own path, and must learn no more from
    it than a player does — the secret can only be deduced from the published board."""
    from datetime import datetime, timezone

    from api.app.schemas.core import RegisterBody
    from api.app.zoopark import safe
    from api.app.zoopark.core import register

    midwindow = datetime(2026, 7, 20, 17, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(safe, "utcnow", lambda: midwindow)
    register(-1001, RegisterBody(nickname="Сфорца"))

    state = tools.call("safe_state", tg_id=-1001, player_id=1, arguments={})
    assert state["ok"] is True and state["is_open"] is True
    assert "secret" not in json.dumps(state, ensure_ascii=False)

    guess = tools.call("safe_guess", tg_id=-1001, player_id=1, arguments={"code": "047312"})
    assert guess["ok"] is True and guess["attempts_left"] == 2
    # The clue is withheld from the rival exactly as it is from a human.
    assert "exact" not in guess


def test_a_rival_gets_no_extra_attempts(db, monkeypatch):
    from datetime import datetime, timezone

    from api.app.schemas.core import RegisterBody
    from api.app.zoopark import safe
    from api.app.zoopark.core import register

    monkeypatch.setattr(safe, "utcnow", lambda: datetime(2026, 7, 20, 17, 0, tzinfo=timezone.utc))
    register(-1001, RegisterBody(nickname="Сфорца"))

    for _ in range(3):
        tools.call("safe_guess", tg_id=-1001, player_id=1, arguments={"code": "111111"})
    refused = tools.call("safe_guess", tg_id=-1001, player_id=1, arguments={"code": "222222"})
    assert refused["ok"] is False


# ── MCP ───────────────────────────────────────────────────────────────────────


def test_mcp_exposes_exactly_the_same_tools():
    """Two copies of a toolset drift. The MCP server must be a protocol over the registry,
    never a second list."""
    from api.bots import mcp_server

    listed = {entry["name"] for entry in mcp_server._tool_list()["tools"]}
    assert listed == set(tools.REGISTRY)


def test_mcp_tool_schemas_are_json_serialisable():
    from api.bots import mcp_server

    json.dumps(mcp_server._tool_list(), ensure_ascii=False)
