"""Forge mutations return enough state for a local client patch."""

from api.app.db.connection import get_session
from api.app.db.models import Item
from api.app.schemas.forge import ForgeCreateBody, ForgeItemIdBody, ForgeSetBody, ForgeSetIdBody
from api.app.zoopark import forge
from api.app.zoopark.catalog import forge_create_cost_usd


def test_create_returns_next_price_and_inactive_sale_skips_income_scan(db, player, grant):
    grant(player, "usd", 1_000_000)

    created = forge.forge_create(player, ForgeCreateBody(currency="usd"))
    assert created["next_cost_usd"] == forge_create_cost_usd(1)

    upgraded = forge.forge_upgrade(player, ForgeItemIdBody(item_id=created["item"]["id"]))
    assert upgraded["item"]["id"] == created["item"]["id"]
    assert upgraded["new_usd"] < created["new_usd"]
    assert "income_rub_per_min" in upgraded
    assert "upkeep_rub_per_min" in upgraded
    assert "income_synced_at" in upgraded
    assert "active_item_bonuses" in upgraded

    sold = forge.forge_sell(player, ForgeItemIdBody(item_id=created["item"]["id"]))
    assert sold["removed_item_id"] == created["item"]["id"]
    assert sold["was_active"] is False
    assert "income_rub_per_min" not in sold

    active_created = forge.forge_create(player, ForgeCreateBody(currency="usd"))
    item_set = forge.forge_set_create(
        player,
        ForgeSetBody(item_ids=[active_created["item"]["id"]], name="Активная сборка"),
    )
    applied = forge.forge_set_apply(player, ForgeSetIdBody(set_id=item_set["set"]["id"]))
    assert applied["active_item_ids"] == [active_created["item"]["id"]]
    assert "upkeep_rub_per_min" in applied
    assert "income_synced_at" in applied
    assert "active_item_bonuses" in applied

    with get_session() as session:
        assert session.query(Item).count() == 1
