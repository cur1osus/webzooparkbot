"""Cocktail rules: the daily reset, and who gets paid for solving it."""

import json
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from api.app.db.connection import get_session
from api.app.db.models import CocktailDay, CocktailRound, CocktailSolve, Player
from api.app.schemas.core import RegisterBody
from api.app.schemas.games import CocktailGuessBody
from api.app.zoopark import games
from api.app.zoopark.core import register


def _register_players(*telegram_ids: int) -> None:
    for index, telegram_id in enumerate(telegram_ids, start=1):
        register(telegram_id, RegisterBody(nickname=f"player-{index}"))


def test_cocktail_resets_at_10_moscow():
    before_reset = datetime(2026, 7, 20, 6, 59, tzinfo=timezone.utc)
    period_day, next_reset = games._cocktail_period(before_reset)
    assert period_day == date(2026, 7, 19)
    assert next_reset == datetime(2026, 7, 20, 7, tzinfo=timezone.utc)

    at_reset = datetime(2026, 7, 20, 7, tzinfo=timezone.utc)
    period_day, next_reset = games._cocktail_period(at_reset)
    assert period_day == date(2026, 7, 20)
    assert next_reset == datetime(2026, 7, 21, 7, tzinfo=timezone.utc)


def test_cocktail_history_persists_and_every_solver_is_paid(db):
    """The first solver is paid double; everyone after is still paid.

    While the prize was winner-take-all the same two players took it five days running and
    the rest stopped playing, which is exactly what contest theory predicts of a contest a
    weaker entrant cannot win.
    """
    _register_players(1001, 1002)

    wrong = ["🍓", "🍓", "🍓", "🍓"]
    first_attempt = games.cocktail_guess(1001, CocktailGuessBody(fruits=wrong))
    assert first_attempt["attempts_left"] == 9
    state = games.cocktail_state(1001)
    assert state["attempts_left"] == 9
    assert len(state["history"]) == 1

    with get_session() as session:
        daily = session.query(CocktailDay).one()
        secret = json.loads(daily.secret)

    winner = games.cocktail_guess(1001, CocktailGuessBody(fruits=secret))
    second = games.cocktail_guess(1002, CocktailGuessBody(fruits=secret))

    assert winner["won"] is True
    assert winner["reward_paw"] == 150
    assert winner["was_first"] is True
    assert second["won"] is True
    assert second["reward_paw"] == 75
    assert second["was_first"] is False
    assert second["solved_today"] == 2
    assert second["winner_nickname"] == "player-1"

    later = games.cocktail_state(1002)
    assert later["winner_nickname"] == "player-1"
    assert later["rewarded"] is True
    assert later["was_first"] is False

    with get_session() as session:
        balances = [session.query(Player).filter_by(telegram_id=tg_id).one().balance_paw for tg_id in (1001, 1002)]
        assert balances == [150, 75]


def test_cocktail_pays_once_even_if_the_round_row_is_reset(db):
    """`solved_at` guards the common path, but the round row is rewritten when the day rolls
    over. The unique key on (player_id, day) is what actually makes the payout idempotent."""
    _register_players(1001)

    games.cocktail_guess(1001, CocktailGuessBody(fruits=["🍓", "🍓", "🍓", "🍓"]))
    with get_session() as session:
        daily = session.query(CocktailDay).one()
        secret = json.loads(daily.secret)

    games.cocktail_guess(1001, CocktailGuessBody(fruits=secret))

    # Wipe the round as the next reset would, leaving the solve record standing.
    with get_session() as session:
        round_ = session.get(CocktailRound, session.query(Player).filter_by(telegram_id=1001).one().id)
        round_.solved_at = None
        round_.attempts = 0
        round_.history = "[]"
        session.commit()

    with pytest.raises(HTTPException):
        games.cocktail_guess(1001, CocktailGuessBody(fruits=secret))

    with get_session() as session:
        assert session.query(Player).filter_by(telegram_id=1001).one().balance_paw == 150
        assert session.query(CocktailSolve).count() == 1
