"""The invariants that keep the economy closed.

Each test names the hole it exists to keep shut. Add to this file when you touch prices.
"""

from __future__ import annotations

import pytest

from api.app.db.connection import get_session
from api.app.db.models import Animal, DailyBonus, Item, ItemProperty, Locality, Player, utcnow
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import economy, forge, games, ledger
from api.app.zoopark.catalog import (
    BANK_FEE_PERCENT,
    BASE_INCOME_RUB_PER_MIN,
    BONUS_REWARD_VALUES,
    BONUS_REWARD_WEIGHTS,
    EXPEDITION_GRADES,
    EXPEDITIONS,
    ITEM_PROPERTIES,
    ITEM_RARITY_DROP_WEIGHTS,
    OUTBREAK_MIN_HEALTHY,
    RARITIES,
    RATE_MAX_RUB_PER_USD,
    RATE_MIN_RUB_PER_USD,
    SOLO_WIN_CHANCE_PCT,
    SPECIES_ID_BY_CODE,
    SPECIES_RARITY_INCOME_MULT,
    expected_gene_income_mult,
    expected_lifespan_minutes,
    expedition_gene_weights,
    expedition_item_drop_chance,
    expedition_item_rarity_weights,
    expedition_loot,
    expedition_max_depth,
    expedition_minutes,
    expedition_rarity_weights,
    expedition_wild_power_range,
    FORGE_CREATE_BASE_USD,
    FORGE_CREATE_PAW,
    FORGE_MAX_ITEM_LEVEL,
    FORGE_MERGE_COST_USD,
    FORGE_SELL_REFUND_RATE,
    FORGE_UPGRADE_BASE_USD,
    ITEM_RARITIES,
    MERCHANT_PRICE_AS_FRACTION_OF_LIFETIME_INCOME,
    PACK_REWARD_RANGES,
    PACK_TIER_ORDER,
    item_sell_refund_paw,
    item_sell_refund_usd,
    lifetime_income_rub,
    merchant_price_rub,
    pack_price_usd_for_tier,
)
from api.app.schemas.economy import BankExchangeBody
from api.app.schemas.forge import ForgeMergeBody


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


class TestDailyBonusRewards:
    def test_reward_tables_have_matching_values_and_weights(self):
        assert set(BONUS_REWARD_VALUES) == {"rub", "usd", "paw"}
        for currency, values in BONUS_REWARD_VALUES.items():
            assert len(values) == len(BONUS_REWARD_WEIGHTS[currency])
            assert all(value > 0 for value in values)
            assert all(weight > 0 for weight in BONUS_REWARD_WEIGHTS[currency])

        assert BONUS_REWARD_VALUES["rub"] == (100, 1_000, 5_000, 1_000_000)
        assert BONUS_REWARD_VALUES["usd"] == (5, 50, 200, 1_000, 1_000_000)
        assert BONUS_REWARD_VALUES["paw"] == tuple(range(10, 51))

    def test_animal_and_locality_rewards_are_claimable(self, db):
        from api.app.schemas.core import RegisterBody
        from api.app.zoopark.core import register
        from api.app.zoopark.season import ensure_player_season
        from api.app.zoopark.status import claim_bonus

        register(7007, RegisterBody(nickname="animal-reward"))
        register(8008, RegisterBody(nickname="locality-reward"))
        with get_session() as session:
            animal_player = session.query(Player).filter_by(telegram_id=7007).one()
            ensure_player_season(session, animal_player)  # called for the season it creates
            session.add(DailyBonus(
                player_id=animal_player.id,
                bonus_date=utcnow().date(),
                currency="animal",
                amount=1,
                reward_code="rabbit",
            ))

            locality_player = session.query(Player).filter_by(telegram_id=8008).one()
            locality_season = ensure_player_season(session, locality_player)
            existing = {
                row.habitat for row in session.query(Locality).filter_by(
                    player_id=locality_player.id,
                    season_id=locality_season.id,
                )
            }
            reward_habitat = next(habitat for habitat in ("desert", "mountains", "forest", "fields", "antarctica") if habitat not in existing)
            session.add(DailyBonus(
                player_id=locality_player.id,
                bonus_date=utcnow().date(),
                currency="locality",
                amount=1,
                reward_code=reward_habitat,
            ))
            session.commit()

        assert claim_bonus(7007)["reward_name"] == "Кролик"
        with get_session() as session:
            bonus_animal = session.query(Animal).join(Player).filter(Player.telegram_id == 7007).one()
            assert bonus_animal.origin == "daily_bonus"
        assert claim_bonus(8008)["reward_code"] == reward_habitat


class TestForgeCannotPrintMoney:
    def test_creating_then_selling_loses_money(self):
        """C-3 of the old audit: forging cost $1 while selling paid a flat $80,000."""
        expected = sum(
            weight * item_sell_refund_usd(0)
            for _rarity, weight in zip(ITEM_RARITIES[:4], ITEM_RARITY_DROP_WEIGHTS, strict=True)
        )
        assert FORGE_CREATE_BASE_USD > expected

    def test_selling_never_returns_the_forge_cost(self):
        assert item_sell_refund_usd(0) < FORGE_CREATE_BASE_USD

    def test_upgrading_then_selling_loses_money(self):
        for level in range(12):
            gain = item_sell_refund_usd(level + 1) - item_sell_refund_usd(level)
            assert gain < FORGE_UPGRADE_BASE_USD * (level + 1)

    def test_merging_costs_more_than_the_result_sells_for(self):
        # Merge is a flat fee; it must stay above the resale of even a max-level item, so a
        # merge-then-sell can never turn a profit.
        assert item_sell_refund_usd(FORGE_MAX_ITEM_LEVEL) < FORGE_MERGE_COST_USD

    def test_a_pawcoin_forged_item_refunds_pawcoins_not_dollars(self):
        """The season-3 exploit: a flat 350🐾 craft resold for a flat $32 000, laundering a
        few Telegram Stars into an order of magnitude of game dollars. A PawCoin-forged item
        must refund PawCoins — 40% of its create price — and *no* dollars for its creation."""
        assert item_sell_refund_usd(0, "forge", "paw") == 0
        assert item_sell_refund_paw("forge", "paw") == round(FORGE_CREATE_PAW * FORGE_SELL_REFUND_RATE)
        # And the refund is a strict loss, like every other forge path: pay 350🐾, get 140🐾.
        assert item_sell_refund_paw("forge", "paw") < FORGE_CREATE_PAW
        # A dollar-forged item is untouched: dollars in, dollars (a partial refund) out.
        assert item_sell_refund_paw("forge", "usd") == 0
        assert item_sell_refund_usd(0, "forge", "usd") == round(FORGE_CREATE_BASE_USD * FORGE_SELL_REFUND_RATE)


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


class TestMerchantIsPricedForTheRebasedEconomy:
    def test_merchant_is_twice_the_blind_pack_fraction(self):
        assert MERCHANT_PRICE_AS_FRACTION_OF_LIFETIME_INCOME == pytest.approx(0.01)

    def test_merchant_price_tracks_genes_and_species_rarity(self):
        base_lifetime = lifetime_income_rub("medium", "medium", "medium")
        rare = merchant_price_rub("medium", "medium", "medium", "rare")
        legendary = merchant_price_rub("medium", "medium", "medium", "legendary")
        assert rare == int(base_lifetime * 0.8 * 0.01)
        assert legendary == int(base_lifetime * 2.6 * 0.01)
        assert legendary > rare


class TestExpeditionsDoNotMintCurrency:
    """Expeditions gained a currency trophy when depth arrived: a raid that only ever paid
    one animal could not scale with the zoo, but a raid that pays cash is a new faucet, and
    the bank (rub → usd) has to stay the real source of dollars."""

    def _grade(self, key: str):
        return next(grade for grade in EXPEDITION_GRADES if grade["key"] == key)

    def _expected_catch_lifetime_rub(self, habitat: str, depth: int) -> float:
        """What the animal this raid captures will earn over its whole life, on average."""
        gene_weights = expedition_gene_weights(habitat, depth)
        rarity_weights = expedition_rarity_weights(habitat, depth)
        rarity_mult = sum(rarity_weights[r] * SPECIES_RARITY_INCOME_MULT[r] for r in RARITIES)
        return (
            BASE_INCOME_RUB_PER_MIN
            * expected_gene_income_mult(gene_weights)
            * rarity_mult
            * expected_lifespan_minutes(gene_weights)
        )

    @pytest.mark.parametrize("habitat", sorted(EXPEDITIONS))
    def test_the_trophy_never_outgrows_the_catch(self, habitat):
        """The captured animal is the reward; the trophy is a garnish on it. If cash ever
        dwarfed the catch, depth would be farmed for rubles and the genetics loop — the
        actual game — would become the side dish."""
        for depth in range(1, expedition_max_depth(habitat) + 1):
            _, _, mean_wild = expedition_wild_power_range(habitat, depth)
            minutes = expedition_minutes(habitat, depth)
            rub, _ = expedition_loot(round(mean_wild), minutes, self._grade("dominant"))
            lifetime = self._expected_catch_lifetime_rub(habitat, depth)
            assert rub < lifetime * 0.25, f"{habitat} depth {depth}: trophy is {rub / lifetime:.0%} of the catch"

    def test_losing_pays_nothing(self):
        for key in ("rout", "defeat"):
            assert expedition_loot(999, 999, self._grade(key)) == (0, 0)

    def test_only_a_dominant_win_mints_dollars(self):
        """Same rule the packs follow: the bank stays the dollar funnel."""
        for grade in EXPEDITION_GRADES:
            _, usd = expedition_loot(180, 240, grade)
            assert (usd > 0) == grade["pays_usd"], grade["key"]
            assert grade["pays_usd"] == (grade["key"] == "dominant")

    def test_the_dollar_trophy_stays_under_a_pack(self):
        """The strongest beast in the game, dominated, must still not pay for a pack — or the
        expedition would fund the pack economy the bank exists to gate."""
        strongest = max(
            expedition_wild_power_range(habitat, depth)[1]
            for habitat in EXPEDITIONS
            for depth in range(1, expedition_max_depth(habitat) + 1)
        )
        _, usd = expedition_loot(strongest, 24 * 60, self._grade("dominant"))
        assert usd < pack_price_usd_for_tier("rare")

    def test_a_deeper_raid_always_pays_more(self):
        """Otherwise the depth ladder would have a rung nobody should ever climb — exactly the
        inversion that made Antarctica strictly dominated by Fields before depth existed."""
        payouts = [
            expedition_loot(
                round(expedition_wild_power_range("antarctica", depth)[2]),
                expedition_minutes("antarctica", depth),
                self._grade("victory"),
            )[0]
            for depth in range(1, 6)
        ]
        assert payouts == sorted(payouts) and payouts[0] > 0


class TestFoundItemsAreNotACurrencyFaucet:
    """Resale is a *refund*: 40% of the $80k an item cost to forge. Once expeditions began
    dropping items, that framing became load-bearing — a found item cost nothing, so paying
    it the create price back would mint $32 000 per drop out of thin air and make raid
    farming the most lucrative action in the game by an order of magnitude."""

    def test_a_found_item_refunds_nothing_it_did_not_cost(self):
        assert item_sell_refund_usd(0, "expedition") == 0
        assert item_sell_refund_usd(0, "forge") > 0

    def test_a_found_item_still_refunds_the_upgrades_bought_for_it(self):
        """Upgrade levels *are* paid for in dollars, so they are a real refund."""
        bare = item_sell_refund_usd(0, "expedition")
        upgraded = item_sell_refund_usd(3, "expedition")
        assert upgraded > bare
        # And never more than was sunk in: upgrading to level 3 costs far more than it returns.
        spent = sum(FORGE_UPGRADE_BASE_USD * (level + 1) for level in range(3))
        assert upgraded < spent

    def test_forge_resale_is_unchanged_for_bought_items(self):
        # A pre-fix / merge-result forge item (NULL create_currency) still refunds dollars.
        assert item_sell_refund_usd(0) == item_sell_refund_usd(0, "forge")
        assert item_sell_refund_usd(0, "forge") == round(FORGE_CREATE_BASE_USD * 0.4)

    def test_a_found_item_cannot_be_laundered_into_a_sellable_one(self, db, player, grant):
        """Merging a found item must not hand back a forged one. It loses money today only
        because the $100k fee happens to exceed the $32k resale — an accident of two numbers,
        not a rule. The origin carries through instead."""
        grant(player, "usd", 10 ** 9)
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            first = forge.roll_expedition_item(session, row.id, depth=3)
            second = forge.roll_expedition_item(session, row.id, depth=3)
            first_id, second_id = first.id, second.id
            session.commit()

        merged = forge.forge_merge(player, ForgeMergeBody(item_id1=first_id, item_id2=second_id))
        with get_session() as session:
            item = session.query(Item).filter_by(id=int(merged["new_item"]["id"])).one()
            assert item.origin == "expedition"
        assert merged["new_item"]["sell_price_usd"] == 0

    def test_a_dropped_item_is_marked_found(self, db, player):
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            item = forge.roll_expedition_item(session, row.id, depth=5)
            assert item.origin == "expedition"
            assert item.rarity != "legendary", "legendary stays merge-only, as with forged rolls"
            assert item.properties, "a dropped item must actually carry properties"
            session.rollback()

    def test_nothing_drops_off_a_raid_that_caught_nothing(self):
        for grade in EXPEDITION_GRADES:
            for depth in range(1, 6):
                chance = expedition_item_drop_chance(depth, grade)
                assert (chance > 0) == grade["captured"], f"{grade['key']} d{depth}"

    def test_deeper_raids_drop_more_and_better(self):
        captured = next(g for g in EXPEDITION_GRADES if g["key"] == "victory")
        chances = [expedition_item_drop_chance(d, captured) for d in range(1, 6)]
        assert chances == sorted(chances) and chances[0] > 0
        # Weight of the two best droppable rarities must climb with depth.
        best = [sum(expedition_item_rarity_weights(d)[2:]) for d in range(1, 6)]
        assert best == sorted(best) and best[0] < best[-1]

    def test_every_depth_rarity_table_is_a_distribution(self):
        for depth in range(1, 6):
            assert sum(expedition_item_rarity_weights(depth)) == pytest.approx(1.0)


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
        # Animal-level integer rounding can add up to one ruble in a tiny test zoo.
        assert after == pytest.approx(before * 1.30, rel=0.01, abs=1)

    def test_discount_bank_lowers_the_rate(self, db, player):
        base = economy.bank(player)["rate_rub_per_usd"]
        _activate(player, "discount_bank", 25)
        assert economy.bank(player)["rate_rub_per_usd"] == int(base * 0.75)

    def test_discount_locality_lowers_the_price(self, db, player):
        from api.app.zoopark.progression import list_localities

        before = list_localities(player)["next_price"]
        _activate(player, "discount_locality", 20)
        assert list_localities(player)["next_price"] == int(before * 0.8)

    def test_locality_ladder_targets_the_two_week_milestone(self):
        from api.app.zoopark.progression import locality_price_rub

        prices = [locality_price_rub(count) for count in range(5)]
        assert prices == [0, 100_000, 150_000, 225_000, 337_500]
        assert sum(prices) == 812_500

    def test_discount_packs_lowers_the_pack_price(self, db, player):
        before = pack_price_usd_for_tier("rare")
        _activate(player, "discount_packs", 40)
        pid = _player_id(player)
        with get_session() as session:
            bonuses = bonuses_module.load(session, pid)
        assert pack_price_usd_for_tier("rare", bonuses.pack_discount_multiplier()) < before

    def test_duel_properties_reach_the_roll(self, db, player):
        _activate(player, "duel_moves", 3)
        _activate(player, "duel_bonus", 5)
        pid = _player_id(player)
        with get_session() as session:
            active = bonuses_module.load(session, pid)
        assert active.total("duel_moves") == 3
        assert active.total("duel_bonus") == 5
        with get_session() as session:
            scores = {games._roll_score(session, pid) for _ in range(50)}
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
        pid = _player_id(player)
        with get_session() as session:
            assert bonuses_module.load(session, pid).total("discount_bank") == 80

    def test_discount_upkeep_lowers_the_stored_maintenance_rate(self, db, player):
        from api.app.zoopark.core import me

        _stock_zoo(player)
        before = me(player)["upkeep_rub_per_min"]
        # The fixture is what makes the assertion below mean something. A single pack animal
        # rolls its genes at random, and a weak roll earns so little that upkeep — 5% of
        # income at the one-animal floor — truncates to 1 ₽/min, where a 30% discount rounds
        # straight back to 1 and `after < before` fails against itself.
        assert before > 1, "the fixture must produce an upkeep a discount can visibly lower"

        _activate(player, "discount_upkeep", 30)
        after = me(player)["upkeep_rub_per_min"]
        assert after < before
        pid = _player_id(player)
        with get_session() as session:
            assert bonuses_module.load(session, pid).total("discount_upkeep") == 30

    def test_active_summary_shows_the_capped_total_not_the_naive_sum(self, db, player):
        """The forge summary must report what the game applies. Two −45% upkeep items sum to
        −90%, but the cap is 50%, so the player must see −50% flagged as maxed — never −90%."""
        from api.app.zoopark.core import me

        _activate(player, "discount_upkeep", 45)
        _activate(player, "discount_upkeep", 45)
        summary = me(player)["active_item_bonuses"]
        upkeep = next(entry for entry in summary if entry["kind"] == "discount_upkeep")
        assert upkeep["value"] == 50  # 90 clipped to the kind's cap
        assert upkeep["capped"] is True
        assert "−50%" in upkeep["label"]

    def test_active_summary_omits_uncapped_kinds_from_the_ceiling_flag(self, db, player):
        """`income_total` has no cap, so a large stack is reported in full and never flagged."""
        from api.app.zoopark.core import me

        _activate(player, "income_total", 45)
        _activate(player, "income_total", 45)
        summary = me(player)["active_item_bonuses"]
        income = next(entry for entry in summary if entry["kind"] == "income_total")
        assert income["value"] == 90
        assert income["capped"] is False


def _stock_zoo(telegram_id: int, count: int = 7) -> None:
    """A deterministic zoo whose upkeep is well clear of integer-rounding granularity.

    Built directly rather than by opening packs, because a pack rolls genes at random and a
    weak roll leaves upkeep at 1 ₽/min — a value no percentage discount can move. Kept below
    `OUTBREAK_MIN_HEALTHY` so a passive disease outbreak cannot strike between two reads and
    change the income the upkeep is derived from.
    """
    from api.app.zoopark.progression import create_animal
    from api.app.zoopark.season import ensure_player_season

    assert count < OUTBREAK_MIN_HEALTHY, "a larger zoo could take an outbreak mid-test"
    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=telegram_id).one()
        season = ensure_player_season(session, row)
        for _ in range(count):
            create_animal(
                session,
                player_id=row.id,
                season_id=season.id,
                origin="pack",
                genes={
                    "gene_survival": "high",
                    "gene_reproduction": "high",
                    "gene_appearance": "high",
                    "gene_size": "high",
                },
                habitat="fields",
                species_id=SPECIES_ID_BY_CODE["dragon"],
            )
        session.commit()


def _player_id(telegram_id: int) -> int:
    """The row id, looked up rather than assumed. It used to be written as a literal 1, which
    held only because SQLite hands out ids again after a delete; MySQL does not."""
    with get_session() as session:
        return session.query(Player).filter_by(telegram_id=telegram_id).one().id


def _activate(telegram_id: int, kind: str, value: int, species_id: int | None = None) -> None:
    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=telegram_id).one()
        item = Item(player_id=row.id, rarity="common", level=0, name="t", emoji="x", is_active=True)
        session.add(item)
        session.flush()
        session.add(ItemProperty(item_id=item.id, kind=kind, value=value, species_id=species_id))
        session.commit()
