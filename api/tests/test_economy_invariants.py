"""The invariants that keep the economy closed.

Each test names the hole it exists to keep shut. Add to this file when you touch prices.
"""

from __future__ import annotations

import pytest

from api.app.db.connection import get_session
from api.app.db.models import Item, ItemProperty, Player
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import economy, games, ledger
from api.app.zoopark.catalog import (
    BANK_FEE_PERCENT,
    ITEM_PROPERTIES,
    ITEM_RARITY_DROP_WEIGHTS,
    RATE_MAX_RUB_PER_USD,
    RATE_MIN_RUB_PER_USD,
    SOLO_WIN_CHANCE_PCT,
    FORGE_CREATE_BASE_USD,
    FORGE_MERGE_BASE_USD,
    FORGE_UPGRADE_BASE_USD,
    ITEM_RARITIES,
    PACK_REWARD_RANGES,
    PACK_TIER_ORDER,
    item_sell_price_usd,
    pack_price_usd_for_tier,
)
from api.app.schemas.economy import BankExchangeBody


class TestBankIsOneWay:
    """C-1: the old bank quoted both directions around a ±15% swing with a 2% spread, so
    buying on a cheap minute and selling on a dear one returned 26% per round trip."""

    def test_the_module_exposes_no_reverse_conversion(self):
        exported = {name for name in dir(economy) if not name.startswith("__")}
        assert "exchange" in exported
        assert not any("usd_to_rub" in name or "sell" in name for name in exported)

    def test_exchange_body_cannot_request_a_direction(self):
        assert set(BankExchangeBody.model_fields) == {"amount_rub", "exchange_all"}

    def test_a_round_trip_is_impossible_by_construction(self, db, player, grant):
        """There is nothing to assert about the spread, because there is no way back."""
        grant(player, "rub", 1_000_000)
        economy.exchange(player, BankExchangeBody(exchange_all=True))
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            reasons = {entry.reason for entry in session.query(ledger.LedgerEntry).filter_by(player_id=row.id)}
        assert "bank_buy_usd" in reasons
        assert not any(reason.startswith("bank_sell") for reason in reasons)

    def test_rate_stays_inside_its_band(self, db):
        rate = economy.RATE_START_RUB_PER_USD
        for _ in range(10_000):
            rate = economy._next_rate(rate)
            assert RATE_MIN_RUB_PER_USD <= rate <= RATE_MAX_RUB_PER_USD

    def test_rate_is_stored_not_derived_from_the_clock(self, db):
        with get_session() as session:
            first = economy.base_rate(session, now=600)
            again = economy.base_rate(session, now=630)  # same minute bucket
            session.commit()
        assert first == again

    def test_a_minute_mints_exactly_one_rate(self, db):
        from api.app.db.models import BankRate

        with get_session() as session:
            economy.base_rate(session, now=600)
            economy.base_rate(session, now=659)
            economy.base_rate(session, now=660)
            session.commit()
            periods = [row.period for row in session.query(BankRate).all()]
        assert sorted(periods) == [10, 11]

    def test_the_house_takes_its_fee(self, db, player, grant):
        grant(player, "rub", 10_000_000)
        with get_session() as session:
            rate = economy.base_rate(session, None)
            session.commit()

        result = economy.exchange(player, BankExchangeBody(amount_rub=rate * 1000))
        assert result["fee_usd"] == 1000 * BANK_FEE_PERCENT // 100
        assert result["received_usd"] == 1000 - result["fee_usd"]

        with get_session() as session:
            assert ledger.treasury_balance(session, "usd") == result["fee_usd"]

    def test_only_the_rubles_converted_are_charged(self, db, player, grant):
        grant(player, "rub", 10_000_000)
        with get_session() as session:
            rate = economy.base_rate(session, None)
            session.commit()

        result = economy.exchange(player, BankExchangeBody(amount_rub=rate * 3 + rate - 1))
        assert result["spent_rub"] == rate * 3
        assert result["new_rub"] == 10_000_000 - rate * 3


class TestForgeCannotPrintMoney:
    def test_creating_then_selling_loses_money(self):
        """C-3 of the old audit: forging cost $1 while selling paid a flat $80,000."""
        expected = sum(
            weight * item_sell_price_usd(rarity, 0)
            for rarity, weight in zip(ITEM_RARITIES[:4], ITEM_RARITY_DROP_WEIGHTS, strict=True)
        )
        assert FORGE_CREATE_BASE_USD > expected

    def test_selling_never_returns_the_forge_cost(self):
        for rarity in ITEM_RARITIES:
            assert item_sell_price_usd(rarity, 0) < FORGE_CREATE_BASE_USD

    def test_upgrading_then_selling_loses_money(self):
        for level in range(12):
            gain = item_sell_price_usd("legendary", level + 1) - item_sell_price_usd("legendary", level)
            assert gain < FORGE_UPGRADE_BASE_USD * (level + 1)

    def test_merging_costs_more_than_the_result_sells_for(self):
        cheapest_merge = FORGE_MERGE_BASE_USD * (1 + 1 + 1)
        assert item_sell_price_usd("legendary", 0) < cheapest_merge


class TestSoloGameKeepsAHouseEdge:
    def test_win_chance_is_below_even(self):
        assert SOLO_WIN_CHANCE_PCT < 50

    def test_no_item_property_touches_a_solo_game(self):
        """A `duel_bonus` refund of 10% would invert the only ruble sink in the casino."""
        for kind, spec in ITEM_PROPERTIES.items():
            assert not spec["applies_to"].startswith("games.start_solo"), kind


class TestPacksArePriced:
    def test_price_doubles_up_the_tier_ladder(self):
        prices = [pack_price_usd_for_tier(t) for t in PACK_TIER_ORDER]
        assert prices == sorted(prices) and prices[0] > 0
        assert prices[1] == prices[0] * 2  # epic is double rare
        assert prices[-1] == prices[0] * 8  # mythic is 8× rare

    def test_paid_packs_cost_dollars_and_run_a_dollar_loss(self):
        """Packs are bought with dollars (so the bank has a purpose), and the dollar
        reward stays below the price — the pack never pays for its own next dollar."""
        for tier in PACK_TIER_ORDER:
            assert PACK_REWARD_RANGES[tier]["usd"][1] < pack_price_usd_for_tier(tier)


class TestEveryItemPropertyIsApplied:
    """C-4: the forge sold artefacts labelled "Общий доход +45%" for Telegram Stars, and
    nothing in the codebase ever read the number."""

    @pytest.mark.parametrize("kind", sorted(ITEM_PROPERTIES))
    def test_property_names_a_live_consumer(self, kind):
        module_name, function_name = ITEM_PROPERTIES[kind]["applies_to"].split(".")
        module = __import__(f"api.app.zoopark.{module_name}", fromlist=[function_name])
        assert hasattr(module, function_name), f"{kind} claims {module_name}.{function_name}"

    def test_income_total_multiplies_income(self, db, player):
        from api.app.zoopark.progression import open_pack
        from api.app.zoopark.core import me

        open_pack(player)
        before = me(player)["income_rub_per_min"]
        _activate(player, "income_total", 30)
        after = me(player)["income_rub_per_min"]
        assert after == pytest.approx(before * 1.30, rel=0.01)

    def test_discount_bank_lowers_the_rate(self, db, player):
        base = economy.bank(player)["rate_rub_per_usd"]
        _activate(player, "discount_bank", 25)
        assert economy.bank(player)["rate_rub_per_usd"] == int(base * 0.75)

    def test_discount_locality_lowers_the_price(self, db, player):
        from api.app.zoopark.progression import list_localities

        before = list_localities(player)["next_price"]
        _activate(player, "discount_locality", 20)
        assert list_localities(player)["next_price"] == int(before * 0.8)

    def test_discount_packs_lowers_the_pack_price(self, db, player):
        before = pack_price_usd_for_tier("rare")
        _activate(player, "discount_packs", 40)
        with get_session() as session:
            bonuses = bonuses_module.load(session, 1)
        assert pack_price_usd_for_tier("rare", bonuses.pack_discount_multiplier()) < before

    def test_duel_properties_reach_the_roll(self, db, player):
        _activate(player, "duel_moves", 3)
        _activate(player, "duel_bonus", 5)
        with get_session() as session:
            active = bonuses_module.load(session, 1)
        assert active.total("duel_moves") == 3
        assert active.total("duel_bonus") == 5
        with get_session() as session:
            scores = {games._roll_score(session, 1) for _ in range(50)}
        assert min(scores) >= 8 + 5  # eight dice, each at least one, plus the flat bonus

    def test_bonus_rerolls_are_spendable(self, db, player):
        from api.app.zoopark.status import daily_bonus, reroll_daily_bonus

        _activate(player, "bonus_rerolls", 2)
        assert daily_bonus(player)["rerolls_left"] == 2
        assert reroll_daily_bonus(player)["rerolls_left"] == 1
        assert reroll_daily_bonus(player)["rerolls_left"] == 0
        with pytest.raises(Exception, match="Перебросы"):
            reroll_daily_bonus(player)

    def test_discount_caps_are_enforced(self, db, player):
        _activate(player, "discount_bank", 60)
        _activate(player, "discount_bank", 60)  # a second item stacks, then clips at 80
        with get_session() as session:
            assert bonuses_module.load(session, 1).total("discount_bank") == 80


def _activate(telegram_id: int, kind: str, value: int, species_id: int | None = None) -> None:
    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=telegram_id).one()
        item = Item(player_id=row.id, rarity="common", level=0, name="t", emoji="x", is_active=True)
        session.add(item)
        session.flush()
        session.add(ItemProperty(item_id=item.id, kind=kind, value=value, species_id=species_id))
        session.commit()
