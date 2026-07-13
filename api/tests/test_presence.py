"""The fast maintenance poll also keeps the compact online roster fresh."""

import pytest
from fastapi import HTTPException

from api.app.schemas.core import RegisterBody
from api.app.db.connection import get_session
from api.app.zoopark import maintenance
from api.app.zoopark.core import maintenance_status, register


def test_maintenance_poll_returns_online_players_and_marks_the_caller(db, player):
    register(1002, RegisterBody(nickname="second"))

    first = maintenance_status(player)
    assert first["online_count"] == 1
    assert [item["nickname"] for item in first["online_players"]] == ["tester"]
    assert first["online_players"][0]["is_me"] is True

    second = maintenance_status(1002)
    assert second["online_count"] == 2
    assert {item["nickname"] for item in second["online_players"]} == {"tester", "second"}
    assert second["online_count"] >= len(second["online_players"])


def test_maintenance_blocks_new_registration(db):
    with get_session() as session:
        maintenance.start(session, 10, "Технический перерыв")
        session.commit()

    with pytest.raises(HTTPException) as error:
        register(1002, RegisterBody(nickname="blocked"))

    assert error.value.status_code == 503

    with get_session() as session:
        maintenance.end(session)
        session.commit()

    assert register(1002, RegisterBody(nickname="allowed"))["ok"] is True
