"""The medals tab is backed by server-derived, lifetime progress."""

from api.app.zoopark.core import me


def test_profile_contains_all_achievements(db, player):
    state = me(player)

    assert len(state["achievements"]) == 10
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
    ]
    assert state["achievements"][0]["value"] == 0
    # Registration grants the first locality, so the third achievement step is already
    # visible without requiring the player to open another screen first.
    assert state["achievements"][7]["value"] == 1
