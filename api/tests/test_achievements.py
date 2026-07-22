"""The medals tab is backed by server-derived, lifetime progress."""

import base64
from datetime import datetime, timezone

from api.app.db.connection import get_session
from api.app.db.models import Animal, Player
from api.app.zoopark.season import active_season
from api.app.zoopark.core import me
from api.app.zoopark.core import set_profile_avatar
from api.app.schemas.core import ProfileAvatarBody
from api.app.zoopark import progression, social
from api.app.zoopark.admin import create_custom_achievement, custom_achievement_image, delete_custom_achievement
from api.app.zoopark.core import register
from api.app.schemas.admin import AdminCreateAchievementBody
from api.app.schemas.core import RegisterBody

import pytest


def test_profile_contains_all_achievements(db, player):
    state = me(player)

    assert len(state["achievements"]) == 16
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
        "perfect_fifty",
    ]
    assert state["achievements"][0]["value"] == 0
    # Registration grants the first locality, so the third achievement step is already
    # visible without requiring the player to open another screen first.
    assert state["achievements"][7]["value"] == 1


def test_perfect_genes_medal_survives_the_death_of_the_animal(db, player):
    """The medal is awarded once: an animal that already counted keeps counting."""

    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        season = active_season(session)
        session.add(
            Animal(
                player_id=row.id,
                season_id=season.id,
                species_id=1,
                habitat="forest",
                origin="pack",
                gene_survival="high",
                gene_reproduction="high",
                gene_appearance="high",
                gene_size="high",
                dies_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                removed_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                removal_reason="released",
            )
        )
        session.commit()

    medal = next(item for item in me(player)["achievements"] if item["id"] == "perfect_fifty")
    assert medal["value"] == 1
    assert medal["target"] == 50


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


def test_admin_can_open_custom_achievement_for_selected_player(db, player):
    register(1002, RegisterBody(nickname="second"))
    image = "data:image/png;base64," + base64.b64encode(b"test-image").decode()

    created = create_custom_achievement(
        474701274,
        AdminCreateAchievementBody(
            title="Особый смотритель",
            description="Получено лично от владельца зоопарка",
            audience="selected",
            player_tg_ids=[1002],
            image_data=image,
        ),
    )

    first_state = me(player)
    second_state = me(1002)
    custom_first = next(item for item in first_state["achievements"] if item["id"] == created["id"])
    custom_second = next(item for item in second_state["achievements"] if item["id"] == created["id"])
    assert custom_first["completed"] is False
    assert custom_second["completed"] is True
    assert custom_second["image_url"] == created["image_url"]
    assert custom_achievement_image(created["id"]) == (b"test-image", "image/png")

    with pytest.raises(Exception, match="Сначала открой"):
        set_profile_avatar(player, ProfileAvatarBody(avatar=f"achievement:{created['id']}"))
    assert set_profile_avatar(1002, ProfileAvatarBody(avatar=f"achievement:{created['id']}"))["profile_emoji"] == f"achievement:{created['id']}"

    assert delete_custom_achievement(474701274, created["id"]) == {"ok": True, "id": created["id"]}
    deleted_state = me(1002)
    assert deleted_state["profile_emoji"] is None
    assert all(item["id"] != created["id"] for item in deleted_state["achievements"])
    with pytest.raises(Exception, match="Изображение не найдено"):
        custom_achievement_image(created["id"])
