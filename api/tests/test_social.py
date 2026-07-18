from api.app.schemas.core import RegisterBody
from api.app.schemas.social import ClanCreateBody, ClanJoinDecisionBody, ClanRequestBody
from api.app.zoopark.core import register
from api.app.zoopark.social import (
    clan_create,
    clan_decide_join_request,
    clan_details,
    clan_join,
    clan_list,
)


def test_clan_join_request_is_reviewed_by_owner(db, player):
    register(1002, RegisterBody(nickname="applicant"))
    created = clan_create(player, ClanCreateBody(name="Night Keepers"))

    before = clan_list(1002)
    clan = before["clans"][0]
    assert clan["id"] == created["id"]
    assert clan["join_request_status"] is None

    requested = clan_join(1002, ClanRequestBody(clan_id=clan["id"]))
    assert requested["status"] == "pending"
    assert "Глава клана рассмотрит" in requested["message"]
    assert clan_list(1002)["clans"][0]["join_request_status"] == "pending"

    owner_details = clan_details(player)
    assert len(owner_details["join_requests"]) == 1
    request_id = owner_details["join_requests"][0]["id"]

    accepted = clan_decide_join_request(
        player,
        ClanJoinDecisionBody(request_id=request_id, decision="accept"),
    )
    assert accepted["decision"] == "accept"
    assert clan_list(1002)["my_clan"]["id"] == clan["id"]
