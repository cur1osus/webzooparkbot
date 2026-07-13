"""Multiplayer lobby, timer and prize-pool rules."""

from datetime import timedelta

from api.app.db.connection import get_session
from api.app.db.models import Player, utcnow
from api.app.schemas.core import RegisterBody
from api.app.schemas.games import DuelCreateBody, SoloStartBody
from api.app.zoopark import games, ledger
from api.app.zoopark.core import register


def _register_players(*telegram_ids: int) -> None:
    for index, telegram_id in enumerate(telegram_ids, start=1):
        register(telegram_id, RegisterBody(nickname=f"player-{index}"))


def _grant_rub(telegram_id: int, amount: int) -> None:
    with get_session() as session:
        player = session.query(Player).filter_by(telegram_id=telegram_id).one()
        ledger.grant(session, player, "rub", amount, "daily_bonus")
        session.commit()


def test_creator_can_join_and_three_players_get_70_20_10(db):
    _register_players(1001, 1002, 1003)
    for telegram_id in (1001, 1002, 1003):
        _grant_rub(telegram_id, 10)

    created = games.create_duel(1001, DuelCreateBody(kind="dice", stake_rub=10))
    game_id = created["game"]["id"]
    assert created["new_rub"] == 10
    assert created["game"]["participant_count"] == 0
    assert created["game"]["max_players"] == 3

    owner_joined = games.join_duel(1001, game_id)
    assert owner_joined["game"]["viewer_joined"] is True
    assert owner_joined["game"]["participant_count"] == 1
    assert owner_joined["game"]["status"] == "open"

    games.join_duel(1002, game_id)
    finished = games.join_duel(1003, game_id)

    assert finished["game"]["status"] == "finished"
    assert finished["game"]["participant_count"] == 3
    assert sorted(participant["reward_rub"] for participant in finished["game"]["participants"]) == [3, 6, 21]

    with get_session() as session:
        balances = [session.query(Player).filter_by(telegram_id=tg_id).one().balance_rub for tg_id in (1001, 1002, 1003)]
        assert sum(balances) == 30


def test_expired_two_player_lobby_uses_70_30_and_timer_resolves(db):
    _register_players(1001, 1002)
    for telegram_id in (1001, 1002):
        _grant_rub(telegram_id, 10)

    created = games.create_duel(1001, DuelCreateBody(kind="dice", stake_rub=10))
    game_id = created["game"]["id"]
    games.join_duel(1001, game_id)
    games.join_duel(1002, game_id)

    with get_session() as session:
        duel = session.get(games.Duel, game_id)
        assert duel is not None
        assert duel.expires_at is not None
        assert duel.expires_at > duel.created_at
        duel.expires_at = utcnow() - timedelta(seconds=1)
        session.commit()

    resolved = games.resolve_duel(1001, game_id)
    assert resolved["game"]["status"] == "finished"
    assert sorted(participant["reward_rub"] for participant in resolved["game"]["participants"]) == [6, 14]


def test_solo_stake_is_calculated_from_locked_balance_percentage(db):
    register(1001, RegisterBody(nickname="solo-player"))
    _grant_rub(1001, 1000)

    result = games.start_solo_game(1001, SoloStartBody(kind="dice", stake_pct=15))

    assert result["stake_rub"] == 150
    assert abs(result["rub_delta"]) == 150
    with get_session() as session:
        balance = session.query(Player).filter_by(telegram_id=1001).one().balance_rub
        assert balance == 1000 + result["rub_delta"]
