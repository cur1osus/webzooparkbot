"""The medals tab is backed by server-derived, lifetime progress."""

from api.app.zoopark.core import me
from api.app.zoopark.core import set_profile_avatar
from api.app.schemas.core import ProfileAvatarBody
from api.app.zoopark import progression, social

import pytest


def test_profile_contains_all_achievements(db, player):
    state = me(player)

    assert len(state["achievements"]) == 15
    assert [item["id"] for item in state["achievements"]] == [
        "first_beast",
        "growing_zoo",
        "collector",
        "first_baby",
        "geneticist",
        "first_expedition",
        "pathfinder",
        "architect",
        "blacksmith",
        "arena_winner",
        "endgame_zoo",
        "endgame_collector",
        "endgame_geneticist",
        "endgame_explorer",
        "endgame_empire",
    ]
    assert state["achievements"][0]["value"] == 0
    # Registration grants the first locality, so the third achievement step is already
    # visible without requiring the player to open another screen first.
    assert state["achievements"][7]["value"] == 1


def test_only_unlocked_achievement_can_become_profile_avatar(db, player):
    with pytest.raises(Exception, match="Сначала открой"):
        set_profile_avatar(player, ProfileAvatarBody(avatar="achievement:first_beast"))

    progression.open_pack(player)
    result = set_profile_avatar(player, ProfileAvatarBody(avatar="achievement:first_beast"))
    assert result["profile_emoji"] == "achievement:first_beast"

    cleared = set_profile_avatar(player, ProfileAvatarBody(avatar=None))
    assert cleared["profile_emoji"] is None


def test_leaderboard_exposes_the_selected_profile_avatar(db, player):
    progression.open_pack(player)
    set_profile_avatar(player, ProfileAvatarBody(avatar="achievement:first_beast"))

    assert social.top(player)["entries"][0]["profile_emoji"] == "achievement:first_beast"
