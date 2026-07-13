from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.app.schemas.core import NicknameColorBody
from api.app.zoopark import core, social


def test_purchased_nickname_color_is_saved_and_returned_in_the_leaderboard(player, grant):
    grant(player, "paw", 75)
    response = core.buy_nickname_color(player, "orchid")

    assert response == {"ok": True, "nickname_color": "orchid", "new_paw_coins": 0}
    assert core.me(player)["nickname_color"] == "orchid"
    assert social.top(player)["entries"][0]["nickname_color"] == "orchid"


def test_nickname_color_must_be_owned_before_it_can_be_selected(player):
    with pytest.raises(HTTPException, match="Неизвестный цвет ника"):
        core.set_nickname_color(player, NicknameColorBody(color="rainbow"))
    with pytest.raises(HTTPException, match="Сначала открой"):
        core.set_nickname_color(player, NicknameColorBody(color="aurora"))


def test_nickname_color_is_charged_only_on_first_purchase(player, grant):
    grant(player, "paw", 500)

    first = core.buy_nickname_color(player, "aurora")
    second = core.buy_nickname_color(player, "aurora")

    assert first["new_paw_coins"] == 250
    assert second["new_paw_coins"] == 250


def test_public_profile_contains_only_public_progress(player):
    profile = social.public_profile(player, player)

    assert profile["rank"] == 1
    assert profile["achievements_total"] == 15
    assert profile["species"] == []
    assert "rub" not in profile
    assert "usd" not in profile
    assert "paw_coins" not in profile
    assert profile["active_items"] == []
