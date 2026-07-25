"""Forge mutations return enough state for a local client patch."""

from api.app.db.connection import get_session
from api.app.db.models import Item
from api.app.schemas.forge import ForgeCreateBody, ForgeItemIdBody
from api.app.zoopark import forge
from api.app.zoopark.catalog import forge_create_cost_usd


def test_create_returns_next_price_and_inactive_sale_skips_income_scan(db, player, grant):
    grant(player, "usd", 1_000_000)

    created = forge.forge_create(player, ForgeCreateBody(currency="usd"))
    assert created["next_cost_usd"] == forge_create_cost_usd(1)

    sold = forge.forge_sell(player, ForgeItemIdBody(item_id=created["item"]["id"]))
    assert sold["removed_item_id"] == created["item"]["id"]
    assert sold["was_active"] is False
    assert "income_rub_per_min" not in sold

    with get_session() as session:
        assert session.query(Item).count() == 0
