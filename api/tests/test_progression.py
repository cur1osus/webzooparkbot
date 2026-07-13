"""Packs, breeding and expeditions, against the GDD."""

from __future__ import annotations

from datetime import timedelta

import pytest

from api.app.db.connection import get_session
from api.app.db.models import Animal, Expedition, LedgerEntry, PackOpening, Player, utcnow
from api.app.zoopark import progression
from api.app.zoopark.catalog import (
    BREED_TIER_INDEX,
    EXPEDITION_SQUAD_MIN,
    GENE_ROLL_WEIGHTS,
    PACK_REWARD_RANGES,
    breed_success_rate,
    combat_power,
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


class TestExpeditionLifecycle:
    def _squad(self, telegram_id: int, grant) -> list[int]:
        grant(telegram_id, "usd", 10 ** 9)  # paid packs cost dollars
        # Rare is always unlocked and reopenable; open it enough times to stock a squad.
        for _ in range(6):
            progression.open_pack(telegram_id, "rare")
        return [a["id"] for a in progression.get_expeditions(telegram_id)["available_animals"]][:3]

    def test_only_one_expedition_may_be_active(self, db, player, grant):
        squad = self._squad(player, grant)
        locality_id = progression.list_localities(player)["localities"][0]["id"]
        progression.start_expedition(player, StartExpeditionBody(locality_id=locality_id, animal_ids=squad))
        with pytest.raises(Exception, match="экспедиц"):
            progression.start_expedition(player, StartExpeditionBody(locality_id=locality_id, animal_ids=squad))

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

    def test_locality_upgrade_reduces_upkeep(self, db, player, grant):
        from api.app.zoopark.core import me
        from api.app.schemas.progression import AssignLocalityBody, UpgradeLocalityBody

        progression.open_pack(player)
        grant(player, "rub", 1_000)
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

    def test_global_development_tracks_upgrade(self, db, player, grant):
        from api.app.schemas.development import UpgradeDevelopmentBody
        from api.app.zoopark import development
        from api.app.zoopark.core import me

        grant(player, "rub", 3_000)
        vet = development.upgrade(player, UpgradeDevelopmentBody(kind="vet"))
        genetics = development.upgrade(player, UpgradeDevelopmentBody(kind="genetics"))

        assert vet["level"] == 1
        assert vet["next_cost_rub"] == 5_000
        assert genetics["level"] == 1
        assert me(player)["vet_level"] == 1
        assert me(player)["genetics_level"] == 1

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
    def test_a_parent_breeds_once_a_day(self, db, player):
        from api.app.schemas.progression import BreedBody

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

    def test_inheritance_favours_the_worse_gene(self):
        results = [progression.inherit_gene("low", "high") for _ in range(4000)]
        share_low = results.count("low") / len(results)
        assert 0.55 < share_low < 0.65  # GDD §6: worse wins 60% of the time

    def test_identical_genes_pass_through(self):
        assert all(progression.inherit_gene("high", "high") == "high" for _ in range(50))


def test_tier_index_is_ordered():
    assert BREED_TIER_INDEX["low"] < BREED_TIER_INDEX["medium"] < BREED_TIER_INDEX["high"]
