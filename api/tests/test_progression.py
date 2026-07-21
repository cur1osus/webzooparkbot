"""Packs, breeding and expeditions, against the GDD."""

from __future__ import annotations

from datetime import timedelta

import pytest

from api.app.db.connection import get_session
from api.app.db.models import Animal, Expedition, LedgerEntry, PackOpening, Player, utcnow
from api.app.zoopark import progression, social
from api.app.zoopark.catalog import (
    BREED_TIER_INDEX,
    EXPEDITION_GRADES,
    EXPEDITION_SQUAD_MAX,
    EXPEDITION_SQUAD_MIN,
    GENE_ROLL_WEIGHTS,
    ITEM_PROPERTIES,
    PACK_REWARD_RANGES,
    breed_success_rate,
    combat_power,
    expedition_corps_power_percent,
    expedition_gene_upgrade_chance,
    expedition_gene_weights,
    expedition_grade,
    expedition_loot,
    expedition_max_depth,
    expedition_minutes,
    expedition_rarity_weights,
    expedition_wild_power_range,
)
from api.app.schemas.progression import StartExpeditionBody


class TestGddNumbers:
    def test_gene_roll_is_forty_forty_twenty(self):
        assert GENE_ROLL_WEIGHTS == (0.40, 0.40, 0.20)

    def test_breed_table_matches_the_gdd(self):
        """GDD §6 gives five rows; the formula also settles the row it forgot."""
        assert breed_success_rate("low", "low") == 0.30
        assert breed_success_rate("low", "medium") == 0.45
        assert breed_success_rate("medium", "medium") == 0.60
        assert breed_success_rate("medium", "high") == 0.75
        assert breed_success_rate("high", "high") == 0.90
        # Неохотно + Активное: absent from the table, 60% by the same formula.
        assert breed_success_rate("low", "high") == 0.60

    def test_combat_power_weights(self):
        assert combat_power("low", "low", "low") == 6
        assert combat_power("high", "high", "high") == 18


class TestPackBundles:
    def test_each_tier_has_a_larger_animal_bundle(self):
        assert PACK_REWARD_RANGES["rare"]["animals"] == (1, 2)
        assert PACK_REWARD_RANGES["epic"]["animals"] == (1, 3)
        assert PACK_REWARD_RANGES["legendary"]["animals"] == (2, 5)
        assert PACK_REWARD_RANGES["mythic"]["animals"] == (3, 6)

    def test_daily_gift_favours_rare_and_starves_the_top_tiers(self):
        from api.app.zoopark.catalog import DAILY_GIFT_TIER_WEIGHTS

        w = DAILY_GIFT_TIER_WEIGHTS
        total = sum(w.values())
        assert 0.50 <= w["rare"] / total <= 0.60          # rare is the common gift
        assert w["mythic"] < w["legendary"] < w["epic"] < w["rare"]  # top tiers rarest

    def test_daily_gift_odds_are_whole_percents_that_cover_every_tier(self):
        odds = {o["tier"]: o["percent"] for o in progression.daily_gift_odds()}
        assert set(odds) == {"rare", "epic", "legendary", "mythic"}
        assert sum(odds.values()) == 100

    def test_opening_a_pack_grants_animal_and_currency_rewards(self, db, player):
        result = progression.open_pack(player)
        rewards = result["rewards"]

        # The free daily gift rolls a random tier, so check against whatever tier dropped.
        tier_range = PACK_REWARD_RANGES[result["tier"]]
        assert tier_range["animals"][0] <= len(result["animals"]) <= tier_range["animals"][1]
        assert result["animal"] == result["animals"][0]
        assert tier_range["rub"][0] <= rewards["rub"] <= tier_range["rub"][1]
        assert tier_range["usd"][0] <= rewards["usd"] <= tier_range["usd"][1]
        assert result["new_rub"] == rewards["rub"]
        assert result["new_usd"] == 1 + rewards["usd"]

        with get_session() as session:
            assert session.query(LedgerEntry).filter_by(reason="pack_reward").count() == 2

    def test_free_gift_is_once_per_day(self, db, player):
        progression.open_pack(player)  # claim the gift
        with pytest.raises(Exception, match="подарок уже получен"):
            progression.open_pack(player)

    def test_tiers_unlock_by_ladder_and_stay_reopenable(self, db, player, grant):
        grant(player, "usd", 10 ** 9)

        # Epic is locked until rare is bought.
        with pytest.raises(Exception, match="ещё не открыт"):
            progression.open_pack(player, "epic")

        progression.open_pack(player, "rare")
        info = progression.packs_info(player)
        unlocked = {t["tier"] for t in info["tiers"] if t["unlocked"]}
        assert "rare" in unlocked and "epic" in unlocked and "legendary" not in unlocked

        # A tier does not lock after opening — rare can be opened again and again.
        progression.open_pack(player, "rare")
        progression.open_pack(player, "epic")  # now unlocked
        progression.open_pack(player, "epic")  # reopenable

    def test_paid_pack_price_grows_by_five_percent_after_each_purchase(self, db, player, grant):
        grant(player, "usd", 10 ** 9)

        before = progression.packs_info(player)
        rare_before = next(t["price"] for t in before["tiers"] if t["tier"] == "rare")
        epic_before = next(t["price"] for t in before["tiers"] if t["tier"] == "epic")

        first = progression.open_pack(player, "rare")
        assert first["price_paid"] == rare_before
        after_first = progression.packs_info(player)
        rare_after_first = next(t["price"] for t in after_first["tiers"] if t["tier"] == "rare")
        epic_after_first = next(t["price"] for t in after_first["tiers"] if t["tier"] == "epic")
        assert rare_after_first > rare_before
        assert epic_after_first > epic_before

        # Moving the opening to yesterday must not reset the season-wide price ladder.
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            opening = session.query(PackOpening).filter_by(player_id=row.id).one()
            opening.opened_at = utcnow() - timedelta(days=1)
            session.commit()
        after_day_change = progression.packs_info(player)
        assert next(t["price"] for t in after_day_change["tiers"] if t["tier"] == "rare") == rare_after_first

        second = progression.open_pack(player, "rare")
        after_second = progression.packs_info(player)
        rare_after_second = next(t["price"] for t in after_second["tiers"] if t["tier"] == "rare")
        assert second["price_paid"] == rare_after_first
        assert rare_after_second > rare_after_first


class TestExpeditionsCanBeLost:
    """C-2: `squad_power >= wild_power` with a summed squad of three-to-five animals and a
    single beast made the weakest legal squad beat the strongest possible beast, 18 >= 18.
    Defeat was unreachable, and with it the whole sickness and curing system."""

    @pytest.mark.parametrize("habitat", sorted(progression.EXPEDITIONS))
    def test_the_weakest_legal_squad_never_beats_the_wild(self, habitat):
        weakest = EXPEDITION_SQUAD_MIN * combat_power("low", "low", "low")
        assert all(weakest < progression.wild_encounter(habitat)[1] for _ in range(200))

    @pytest.mark.parametrize("habitat", sorted(progression.EXPEDITIONS))
    def test_an_average_squad_wins_sometimes_and_loses_sometimes(self, habitat):
        average = 4 * combat_power("medium", "medium", "medium")
        outcomes = {average >= progression.wild_encounter(habitat)[1] for _ in range(500)}
        assert outcomes == {True, False}, f"{habitat} has only one possible outcome"

    def test_harder_habitats_are_harder(self):
        average = 4 * combat_power("medium", "medium", "medium")

        def win_rate(habitat: str) -> float:
            trials = 4000
            return sum(average >= progression.wild_encounter(habitat)[1] for _ in range(trials)) / trials

        assert win_rate("fields") > win_rate("mountains") > win_rate("antarctica")


class TestSquadPowerIsWorthInvestingIn:
    """The defect this whole subsystem was rebuilt around.

    `combat_power` tops out at 18, so five animals topped out at 90 while the strongest
    possible beast was int(18 × 3.2) = 57. Every squad above 57 won 100% of encounters in
    every habitat — five plain "medium" animals already scored 60 — and because the beast's
    genes were rolled without reference to the squad, a 90-power squad drew exactly the same
    reward as a 60-power one. Power above the threshold bought *nothing*.
    """

    def test_depth_outruns_the_gene_ceiling(self):
        """No squad, however perfect, trivialises the deepest raid."""
        best_possible_squad = EXPEDITION_SQUAD_MAX * combat_power("high", "high", "high")
        _, strongest_shallow, _ = expedition_wild_power_range("antarctica", 1)
        _, strongest_deep, _ = expedition_wild_power_range("antarctica", 5)

        assert best_possible_squad > strongest_shallow, "depth 1 must stay winnable on genes alone"
        assert best_possible_squad < strongest_deep, "genes alone must never clear a depth-5 beast"

    def test_the_two_non_gene_axes_reach_the_deepest_raid_and_no_further(self):
        """The forge and the corps exist because genes cannot pay for depth. Together they
        must clear a depth-5 raid reliably — and never dominate it, or the ceiling is back."""
        maxed = 1 + (ITEM_PROPERTIES["expedition_power"]["cap"] + expedition_corps_power_percent(5)) / 100
        full_build = int(EXPEDITION_SQUAD_MAX * combat_power("high", "high", "high") * maxed)
        _, strongest, mean = expedition_wild_power_range("antarctica", 5)

        assert expedition_grade(full_build / mean)["captured"], "a full build must beat an average lair beast"
        assert full_build > strongest, "a full build must survive even the worst roll"
        assert expedition_grade(full_build / mean)["key"] != "dominant", "depth 5 must never be farmable"

    def test_surplus_power_buys_a_better_catch(self):
        """Overkill upgrades the catch's genes — the mechanism that makes power pay past the
        win threshold instead of falling off a cliff."""
        assert expedition_gene_upgrade_chance(1.0) == 0
        assert expedition_gene_upgrade_chance(1.2) == 0
        ramp = [expedition_gene_upgrade_chance(r) for r in (1.4, 1.8, 2.2, 2.6)]
        assert ramp == sorted(ramp) and ramp[0] > 0
        assert expedition_gene_upgrade_chance(99) == pytest.approx(0.5), "must saturate, never guarantee"

    def test_the_win_threshold_is_a_gradient_not_a_cliff(self):
        grades = [expedition_grade(r)["key"] for r in (0.5, 0.8, 1.0, 1.3, 1.8, 2.5)]
        assert grades == ["rout", "defeat", "pyrrhic", "victory", "confident", "dominant"]
        # Only an outright rout still kills: a narrow loss costs health, not a life.
        assert [g["key"] for g in EXPEDITION_GRADES if g["casualty"]] == ["rout"]

    def test_a_squad_of_mediums_no_longer_wins_everything(self):
        """The exact symptom: five medium animals used to beat every beast in the game."""
        five_mediums = EXPEDITION_SQUAD_MAX * combat_power("medium", "medium", "medium")
        _, strongest_deep, mean_deep = expedition_wild_power_range("antarctica", 5)
        assert five_mediums < mean_deep
        assert not expedition_grade(five_mediums / mean_deep)["captured"]


class TestTheDifficultyLadderPaysForItself:
    """`roll_species_id` ignored the habitat, so Antarctica dropped the same species as
    Fields for four times the wall-clock. The hardest habitat paid the worst per hour and
    was strictly dominated — nobody had a reason to leave Fields."""

    def test_rarity_climbs_with_the_habitat(self):
        legendary = [
            expedition_rarity_weights(habitat, 1)["legendary"]
            for habitat in ("fields", "desert", "mountains", "antarctica")
        ]
        assert legendary == sorted(legendary)
        assert legendary[0] < legendary[-1]

    def test_rarity_climbs_with_depth(self):
        by_depth = [expedition_rarity_weights("antarctica", d)["legendary"] for d in range(1, 6)]
        assert by_depth == sorted(by_depth) and by_depth[0] < by_depth[-1]

    def test_only_the_hardest_habitat_reaches_the_richest_table(self):
        """The habitat caps the depth it offers — that cap *is* the ladder."""
        caps = {habitat: expedition_max_depth(habitat) for habitat in progression.EXPEDITIONS}
        assert caps["fields"] < caps["desert"] <= caps["mountains"] < caps["antarctica"] == 5
        best_fields = expedition_rarity_weights("fields", caps["fields"])["legendary"]
        best_antarctica = expedition_rarity_weights("antarctica", caps["antarctica"])["legendary"]
        assert best_fields < best_antarctica

    def test_a_deeper_raid_is_stronger_slower_and_richer(self):
        power = [expedition_wild_power_range("antarctica", d)[2] for d in range(1, 6)]
        minutes = [expedition_minutes("antarctica", d) for d in range(1, 6)]
        assert power == sorted(power) and minutes == sorted(minutes)

    def test_depth_one_is_exactly_what_shipped_before_depth_existed(self):
        """Every in-flight expedition keeps its odds across the migration."""
        for habitat, spec in progression.EXPEDITIONS.items():
            assert expedition_gene_weights(habitat, 1) == spec["gene_weights"]
            assert expedition_minutes(habitat, 1) == spec["minutes"]


class TestExpeditionLifecycle:
    def _stock(self, telegram_id: int, grant, packs: int = 6) -> None:
        grant(telegram_id, "usd", 10 ** 9)  # paid packs cost dollars
        # Rare is always unlocked and reopenable; open it enough times to stock a squad.
        for _ in range(packs):
            progression.open_pack(telegram_id, "rare")

    def _squad(self, telegram_id: int, grant) -> list[int]:
        self._stock(telegram_id, grant)
        return [a["id"] for a in progression.get_expeditions(telegram_id)["available_animals"]][:3]

    def _free_squad(self, telegram_id: int, size: int = 3) -> list[int]:
        """Three animals not already committed to a raid."""
        return [a["id"] for a in progression.get_expeditions(telegram_id)["available_animals"]][:size]

    def test_only_one_expedition_per_locality(self, db, player, grant):
        squad = self._squad(player, grant)
        locality_id = progression.list_localities(player)["localities"][0]["id"]
        progression.start_expedition(player, StartExpeditionBody(locality_id=locality_id, animal_ids=squad))
        with pytest.raises(Exception, match="экспедиц"):
            progression.start_expedition(
                player, StartExpeditionBody(locality_id=locality_id, animal_ids=self._free_squad(player))
            )

    def test_localities_run_in_parallel(self, db, player, grant):
        """One raid per zoo capped the feature's whole output at one animal per trip, so it
        faded to noise exactly as the zoo grew. Throughput now follows locality investment."""
        self._stock(player, grant, packs=14)
        grant(player, "rub", 10 ** 9)
        first, second = self._buy_two_localities(player)

        progression.start_expedition(player, StartExpeditionBody(locality_id=first, animal_ids=self._free_squad(player)))
        progression.start_expedition(player, StartExpeditionBody(locality_id=second, animal_ids=self._free_squad(player)))

        info = progression.get_expeditions(player)
        assert {e["locality_id"] for e in info["expeditions"]} == {first, second}
        assert {loc["id"] for loc in info["localities"] if loc["busy"]} == {first, second}

    def _buy_two_localities(self, telegram_id: int) -> tuple[int, int]:
        from api.app.schemas.progression import BuyLocalityBody

        taken = set(progression.list_localities(telegram_id)["habitats_taken"])
        free = next(h for h in ("fields", "desert", "forest", "mountains", "antarctica") if h not in taken)
        progression.buy_locality(telegram_id, BuyLocalityBody(habitat=free))
        localities = progression.list_localities(telegram_id)["localities"]
        return localities[0]["id"], localities[1]["id"]

    def _locality_for(self, telegram_id: int, habitat: str) -> int:
        """The player's locality in `habitat`, bought if the free starting roll missed it.

        The first locality is random (GDD §5), so a test that merely hopes for one habitat
        would skip most runs and assert nothing.
        """
        from api.app.schemas.progression import BuyLocalityBody

        for locality in progression.list_localities(telegram_id)["localities"]:
            if locality["habitat"] == habitat:
                return locality["id"]
        progression.buy_locality(telegram_id, BuyLocalityBody(habitat=habitat))
        return next(
            locality["id"]
            for locality in progression.list_localities(telegram_id)["localities"]
            if locality["habitat"] == habitat
        )

    def test_a_habitat_caps_the_depth_it_offers(self, db, player, grant):
        """The cap is the ladder: Fields must not print Antarctica's legendary table."""
        squad = self._squad(player, grant)
        grant(player, "rub", 10 ** 9)
        fields_id = self._locality_for(player, "fields")
        fields = next(
            loc for loc in progression.get_expeditions(player)["localities"] if loc["id"] == fields_id
        )

        assert fields["max_depth"] == 2
        assert [option["depth"] for option in fields["depths"]] == [1, 2]
        with pytest.raises(Exception, match="глубина"):
            progression.start_expedition(
                player, StartExpeditionBody(locality_id=fields_id, animal_ids=squad, depth=5)
            )

    def test_the_deepest_raid_is_reachable_where_the_ladder_allows_it(self, db, player, grant):
        squad = self._squad(player, grant)
        grant(player, "rub", 10 ** 9)
        antarctica_id = self._locality_for(player, "antarctica")
        started = progression.start_expedition(
            player, StartExpeditionBody(locality_id=antarctica_id, animal_ids=squad, depth=5)
        )["expedition"]
        assert started["depth"] == 5
        assert started["depth_name"] == "Логово"

    def test_depth_lengthens_the_trip_and_strengthens_the_beast(self, db, player, grant):
        squad = self._squad(player, grant)
        localities = progression.get_expeditions(player)["localities"]
        locality = localities[0]
        if locality["max_depth"] < 2:
            pytest.skip("this habitat offers a single depth")

        started = progression.start_expedition(
            player, StartExpeditionBody(locality_id=locality["id"], animal_ids=squad, depth=2)
        )["expedition"]
        assert started["depth"] == 2
        shallow, deep = locality["depths"][0], locality["depths"][1]
        assert deep["minutes"] > shallow["minutes"]
        assert deep["wild_power_avg"] > shallow["wild_power_avg"]

    def test_a_squad_animal_cannot_be_listed_twice(self, db, player, grant):
        squad = self._squad(player, grant)
        locality_id = progression.list_localities(player)["localities"][0]["id"]
        with pytest.raises(Exception, match="дважды"):
            progression.start_expedition(
                player, StartExpeditionBody(locality_id=locality_id, animal_ids=[squad[0]] * 3)
            )

    def test_animals_on_an_expedition_stop_earning(self, db, player, grant):
        squad = self._squad(player, grant)
        locality_id = progression.list_localities(player)["localities"][0]["id"]
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            before = row.income_rub_per_min

        progression.start_expedition(player, StartExpeditionBody(locality_id=locality_id, animal_ids=squad))
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            assert row.income_rub_per_min < before

    def test_animals_on_an_expedition_are_hidden_from_zoo(self, db, player, grant):
        from api.app.zoopark.core import me

        squad = self._squad(player, grant)
        locality_id = progression.list_localities(player)["localities"][0]["id"]
        progression.start_expedition(player, StartExpeditionBody(locality_id=locality_id, animal_ids=squad))

        state = me(player)
        visible_ids = {animal["id"] for animal in state["animals"]}
        assert not visible_ids.intersection(squad)
        assert state["live_animals_count"] == len(state["animals"])

        public_profile = social.public_profile(player, player)
        assert public_profile["animals_count"] == len(state["animals"])
        assert public_profile["animals_count"] < len(squad) + len(state["animals"])

    def test_locality_upgrade_reduces_upkeep(self, db, player, grant):
        from api.app.zoopark.core import me
        from api.app.schemas.progression import AssignLocalityBody, UpgradeLocalityBody

        progression.open_pack(player)
        grant(player, "rub", 20_000)
        locality_id = progression.list_localities(player)["localities"][0]["id"]
        animal_id = progression.list_available_animals(player)["animals"][0]["id"]
        progression.assign_locality(player, AssignLocalityBody(animal_id=animal_id, locality_id=locality_id))
        before = me(player)
        result = progression.upgrade_locality(player, UpgradeLocalityBody(locality_id=locality_id))
        after = me(player)

        assert result["level"] == 1
        assert result["upkeep_discount_percent"] == 1
        assert result["next_upkeep_discount_percent"] == 3
        assert after["income_rub_per_min"] == before["income_rub_per_min"]
        assert after["upkeep_rub_per_min"] < before["upkeep_rub_per_min"]

    def test_the_animal_list_agrees_with_me_about_the_habitat_bonus(self, db, player, grant):
        """`/api/animals` used to compute every animal as if it lived nowhere, so it reported
        `habitat_bonus: false` and a smaller income than `/api/me` for the very same animal."""
        from api.app.zoopark.core import me
        from api.app.schemas.progression import AssignLocalityBody, BuyLocalityBody

        progression.open_pack(player)
        grant(player, "rub", 1_000_000)
        animal = progression.list_available_animals(player)["animals"][0]
        localities = progression.list_localities(player)["localities"]
        locality = next(
            (loc for loc in localities if loc["habitat"] == animal["habitat"]),
            None,
        ) or progression.buy_locality(player, BuyLocalityBody(habitat=animal["habitat"]))
        progression.assign_locality(player, AssignLocalityBody(animal_id=animal["id"], locality_id=locality["id"]))

        listed = next(a for a in progression.list_available_animals(player)["animals"] if a["id"] == animal["id"])
        from_me = next(a for a in me(player)["animals"] if a["id"] == animal["id"])

        assert listed["habitat_bonus"] is True
        assert listed["income"] == from_me["income"]

    def test_global_development_tracks_upgrade(self, db, player, grant):
        from api.app.schemas.development import UpgradeDevelopmentBody
        from api.app.zoopark import development
        from api.app.zoopark.core import me

        grant(player, "rub", 60_000)
        vet = development.upgrade(player, UpgradeDevelopmentBody(kind="vet"))
        genetics = development.upgrade(player, UpgradeDevelopmentBody(kind="genetics"))

        assert vet["level"] == 1
        assert vet["next_cost_rub"] == 100_000
        assert genetics["level"] == 1
        assert me(player)["vet_level"] == 1
        assert me(player)["genetics_level"] == 1

    def test_the_trophy_comes_from_the_depth_not_the_clock(self, db, player, grant, monkeypatch):
        """The trophy is priced off the raid's designed length. Reading the gap between
        `started_at` and `ends_at` instead made it collapse to zero rubles whenever anything
        shifted the timestamp — while still paying dollars, which do not scale with time."""
        self._stock(player, grant, packs=14)
        grant(player, "rub", 10 ** 9)
        locality_id = self._locality_for(player, "fields")
        squad = self._free_squad(player, size=EXPEDITION_SQUAD_MAX)
        started = progression.start_expedition(
            player, StartExpeditionBody(locality_id=locality_id, animal_ids=squad, depth=1)
        )

        # Pin the beast to the weakest one there is, so the squad certainly wins and this
        # asserts on the trophy rather than on a gene roll.
        weakest = ({k: "low" for k in ("gene_survival", "gene_reproduction", "gene_appearance", "gene_size")}, 1)
        monkeypatch.setattr(progression, "wild_encounter", lambda *_args, **_kwargs: weakest)

        # Land the raid the instant it launched — the shift the old code silently read as
        # "this expedition took no time, so it earned nothing".
        with get_session() as session:
            expedition = session.query(Expedition).filter_by(id=started["expedition"]["id"]).one()
            expedition.ends_at = expedition.started_at
            session.commit()

        result = progression.finish_expedition(player, started["expedition"]["id"])["result"]
        assert result["grade"] == "dominant", "the weakest possible beast must be dominated"
        expected_rub, expected_usd = expedition_loot(
            result["wild_power"], expedition_minutes("fields", 1), expedition_grade(result["ratio"])
        )
        assert result["loot"] == {"rub": expected_rub, "usd": expected_usd}
        assert result["loot"]["rub"] > 0, "a zeroed clock must not zero the trophy"

    def test_finishing_early_is_refused(self, db, player, grant):
        squad = self._squad(player, grant)
        locality_id = progression.list_localities(player)["localities"][0]["id"]
        progression.start_expedition(player, StartExpeditionBody(locality_id=locality_id, animal_ids=squad))
        with pytest.raises(Exception, match="ещё не завершена"):
            progression.finish_expedition(player)

    def test_finishing_twice_is_refused(self, db, player, grant):
        squad = self._squad(player, grant)
        locality_id = progression.list_localities(player)["localities"][0]["id"]
        progression.start_expedition(player, StartExpeditionBody(locality_id=locality_id, animal_ids=squad))
        with get_session() as session:
            expedition = session.query(Expedition).one()
            expedition.ends_at = utcnow()
            session.commit()

        result = progression.finish_expedition(player)["result"]
        assert result["outcome"] in ("victory", "defeat")
        assert result["wild"]["species_name"]
        if result["outcome"] == "victory":
            assert result["captured_animal"]["species_code"] == result["wild"]["species_code"]
        with pytest.raises(Exception, match="Нет активной"):
            progression.finish_expedition(player)


class TestDeathIsDerived:
    """I-2: `/api/me` used to serve animals whose `dies_at` had passed, because liveness
    was a separate `is_alive` column that only some endpoints remembered to sweep."""

    def test_an_expired_animal_disappears_from_the_state(self, db, player):
        from api.app.zoopark.core import me

        result = progression.open_pack(player)
        assert me(player)["live_animals_count"] == len(result["animals"])

        with get_session() as session:
            session.query(Animal).update({"dies_at": utcnow()})
            session.commit()

        state = me(player)
        assert state["live_animals_count"] == 0
        assert state["income_rub_per_min"] == 0


class TestBreeding:
    def test_a_parent_breeds_once_a_day(self, db, player, grant):
        from api.app.schemas.progression import BreedBody

        grant(player, "rub", 10_000_000)  # breeding now costs rubles
        first = progression.open_pack(player)["animals"][0]
        with get_session() as session:
            parent = session.get(Animal, first["id"])
            assert parent is not None
            mate = progression.create_animal(
                session,
                player_id=parent.player_id,
                season_id=parent.season_id,
                origin="pack",
                genes={
                    "gene_survival": parent.gene_survival,
                    "gene_reproduction": parent.gene_reproduction,
                    "gene_appearance": parent.gene_appearance,
                    "gene_size": parent.gene_size,
                },
                habitat=parent.habitat,
                species_id=parent.species_id,
            )
            parent_id = parent.id
            mate_id = mate.id
            session.commit()

        result = progression.breed(player, BreedBody(animal_id_1=parent_id, animal_id_2=mate_id))
        if result["success"]:
            assert len(result["inherited_genes"]) == 4
            assert {entry["gene"] for entry in result["inherited_genes"]} == {
                "survival", "reproduction", "appearance", "size_trait"
            }
        with pytest.raises(Exception, match="уже скрещивалось"):
            progression.breed(player, BreedBody(animal_id_1=parent_id, animal_id_2=mate_id))

    def test_breeding_charges_rubles_on_the_attempt(self, db, player, grant):
        from api.app.schemas.progression import BreedBody
        from api.app.zoopark import ledger
        from api.app.zoopark.catalog import breed_cost_rub
        from api.app.zoopark.income import animal_base_income_rub_per_min

        grant(player, "rub", 10_000_000)
        first = progression.open_pack(player)["animals"][0]
        with get_session() as session:
            parent = session.get(Animal, first["id"])
            mate = progression.create_animal(
                session,
                player_id=parent.player_id,
                season_id=parent.season_id,
                origin="pack",
                genes={
                    "gene_survival": parent.gene_survival,
                    "gene_reproduction": parent.gene_reproduction,
                    "gene_appearance": parent.gene_appearance,
                    "gene_size": parent.gene_size,
                },
                habitat=parent.habitat,
                species_id=parent.species_id,
            )
            expected = breed_cost_rub(
                animal_base_income_rub_per_min(parent), animal_base_income_rub_per_min(mate)
            )
            row = session.query(Player).filter_by(telegram_id=player).one()
            before = ledger.balance(row, "rub")
            parent_id, mate_id = parent.id, mate.id
            session.commit()

        result = progression.breed(player, BreedBody(animal_id_1=parent_id, animal_id_2=mate_id))
        assert result["cost_rub"] == expected
        # Income may accrue between the two reads, so assert the fee was withdrawn, not equality.
        assert result["new_rub"] <= before - expected

    def test_breeding_is_refused_without_the_fee(self, db, player):
        from api.app.schemas.progression import BreedBody

        first = progression.open_pack(player)["animals"][0]
        with get_session() as session:
            parent = session.get(Animal, first["id"])
            mate = progression.create_animal(
                session,
                player_id=parent.player_id,
                season_id=parent.season_id,
                origin="pack",
                genes={
                    "gene_survival": parent.gene_survival,
                    "gene_reproduction": parent.gene_reproduction,
                    "gene_appearance": parent.gene_appearance,
                    "gene_size": parent.gene_size,
                },
                habitat=parent.habitat,
                species_id=parent.species_id,
            )
            parent_id, mate_id = parent.id, mate.id
            session.commit()

        with pytest.raises(Exception, match="Недостаточно средств"):
            progression.breed(player, BreedBody(animal_id_1=parent_id, animal_id_2=mate_id))

    def test_inheritance_favours_the_worse_gene(self):
        results = [progression.inherit_gene("low", "high") for _ in range(4000)]
        share_low = results.count("low") / len(results)
        assert 0.55 < share_low < 0.65  # GDD §6: worse wins 60% of the time

    def test_identical_genes_pass_through(self):
        assert all(progression.inherit_gene("high", "high") == "high" for _ in range(50))


def test_tier_index_is_ordered():
    assert BREED_TIER_INDEX["low"] < BREED_TIER_INDEX["medium"] < BREED_TIER_INDEX["high"]
