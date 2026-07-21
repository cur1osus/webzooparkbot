"""Income, upkeep and accrual."""

from __future__ import annotations

from datetime import timedelta

import pytest

from api.app.db.connection import get_session
from api.app.db.models import Player, utcnow
from api.app.zoopark import income, ledger
from api.app.zoopark.catalog import (
    BASE_INCOME_RUB_PER_MIN,
    HABITAT_MATCH_BONUS,
    SPECIES_RARITY_INCOME_MULT,
    gene_income_mult,
)


class TestFormula:
    def test_gdd_best_and_worst_case(self):
        """GDD §3: best 4.095x base, worst 0.336x. A ~12:1 spread."""
        best = gene_income_mult("high", "high", "high") * HABITAT_MATCH_BONUS
        worst = gene_income_mult("low", "low", "low")
        assert best == pytest.approx(4.095)
        assert worst == pytest.approx(0.336)
        assert best / worst == pytest.approx(12.19, rel=0.01)

    def test_habitat_match_multiplies_by_one_and_a_half(self):
        plain = income.animal_income_rub_per_min(
            survival="medium", appearance="medium", size="medium", habitat_matches=False
        )
        matched = income.animal_income_rub_per_min(
            survival="medium", appearance="medium", size="medium", habitat_matches=True
        )
        assert plain == BASE_INCOME_RUB_PER_MIN
        assert matched == int(BASE_INCOME_RUB_PER_MIN * HABITAT_MATCH_BONUS)

    def test_species_rarity_defines_a_meaningful_income_baseline(self):
        income_by_rarity = {
            rarity: income.animal_income_rub_per_min(
                survival="medium",
                appearance="medium",
                size="medium",
                habitat_matches=False,
                species_rarity=rarity,
            )
            for rarity in SPECIES_RARITY_INCOME_MULT
        }
        assert income_by_rarity == {"rare": 40, "epic": 60, "mythic": 90, "legendary": 130}
        assert income_by_rarity["rare"] < income_by_rarity["epic"] < income_by_rarity["mythic"] < income_by_rarity["legendary"]

    def test_a_sick_animal_earns_half(self):
        healthy = income.animal_income_rub_per_min(
            survival="medium", appearance="medium", size="medium", habitat_matches=False
        )
        sick = income.animal_income_rub_per_min(
            survival="medium", appearance="medium", size="medium", habitat_matches=False, is_sick=True
        )
        assert sick == healthy // 2


class TestDiversity:
    def test_a_monopoly_scores_one_effective_species(self):
        assert income.effective_species_count([100]) == pytest.approx(1.0)

    def test_an_even_spread_scores_the_species_count(self):
        assert income.effective_species_count([10, 10, 10, 10]) == pytest.approx(4.0)

    def test_a_lopsided_zoo_scores_less_than_its_species_count(self):
        """A raw `len(species)` would pay the same for both of these."""
        even = income.effective_species_count([10, 10, 10, 10])
        lopsided = income.effective_species_count([97, 1, 1, 1])
        assert lopsided < 2 < even

    def test_an_empty_zoo_has_no_bonus(self):
        assert income.diversity_multiplier([]) == 1.0


class TestUpkeep:
    def test_it_grows_with_the_zoo(self):
        one = income.upkeep_rub_per_min(1_000_000, 1)
        ten = income.upkeep_rub_per_min(1_000_000, 10)
        hundred = income.upkeep_rub_per_min(1_000_000, 100)
        assert one < ten < hundred

    def test_it_is_capped(self):
        assert income.upkeep_rub_per_min(1_000_000, 10 ** 9) == 450_000

    def test_no_animals_means_no_upkeep(self):
        assert income.upkeep_rub_per_min(0, 0) == 0


class TestAccrual:
    def test_a_fraction_of_a_ruble_does_not_reset_the_clock(self, db, player):
        """A client polling once a second used to lose every ruble to `trunc()`."""
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            row.income_rub_per_min = 3
            row.upkeep_rub_per_min = 0
            row.income_synced_at = utcnow()
            session.commit()

        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            before = row.income_synced_at
            assert income.accrue(session, row) == 0
            assert row.income_synced_at == before
            session.commit()

    def test_polling_in_a_loop_earns_no_more_than_waiting(self, db, player):
        """`GET /api/me` accrues and is not rate limited, so the accrual has to be immune to
        how often it is called. It was not: the clock was advanced to a `datetime` carrying
        microseconds, MySQL's DATETIME dropped them, and each poll re-billed the fraction it
        had already been paid for. Against a real MySQL that came to 258x the honest rate."""
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            row.income_rub_per_min = 3323
            row.upkeep_rub_per_min = 0
            row.income_synced_at = utcnow() - timedelta(minutes=5)
            session.commit()

        # Whatever the storage does to the anchor, a thousand polls covering the same five
        # minutes must pay the same five minutes.
        for _ in range(1000):
            with get_session() as session:
                row = session.query(Player).filter_by(telegram_id=player).one()
                income.accrue(session, row)
                session.commit()

        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            earned = ledger.balance(row, "rub")
        assert 3323 * 5 <= earned <= 3323 * 6, f"начислено {earned} ₽ вместо ~{3323 * 5}"

    def test_time_passing_pays_out(self, db, player):
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            row.income_rub_per_min = 600
            row.upkeep_rub_per_min = 100
            # Anchored on a whole second: accrual counts whole seconds, and MySQL rounds a
            # DATETIME to one while SQLite keeps the microseconds, so a fractional anchor
            # makes the expected payout differ by an engine's rounding rather than by rate.
            row.income_synced_at = (utcnow() - timedelta(minutes=10)).replace(microsecond=0)
            session.commit()

        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            assert income.accrue(session, row) == 5000  # (600 - 100) * 10
            assert ledger.balance(row, "rub") == 5000
            session.commit()

    def test_upkeep_empties_a_balance_but_never_overdraws_it(self, db, player, grant):
        grant(player, "rub", 100)
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            row.income_rub_per_min = 0
            row.upkeep_rub_per_min = 1000
            row.income_synced_at = utcnow() - timedelta(minutes=10)
            session.commit()

        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            assert income.accrue(session, row) == -100
            assert ledger.balance(row, "rub") == 0
            session.commit()


class TestDiseaseOutbreak:
    _GENES = {
        "gene_survival": "high",
        "gene_reproduction": "high",
        "gene_appearance": "high",
        "gene_size": "high",
    }

    def _stock_zoo(self, session, telegram_id, count):
        from api.app.db.models import Player
        from api.app.zoopark.progression import create_animal
        from api.app.zoopark.season import ensure_player_season

        row = session.query(Player).filter_by(telegram_id=telegram_id).one()
        season = ensure_player_season(session, row)
        for _ in range(count):
            create_animal(
                session,
                player_id=row.id,
                season_id=season.id,
                origin="pack",
                genes=dict(self._GENES),
                habitat="forest",
            )
        return row

    def _sick_count(self, telegram_id):
        from api.app.db.models import Animal, Player

        with get_session() as session:
            player_id = session.query(Player).filter_by(telegram_id=telegram_id).one().id
            return (
                session.query(Animal)
                .filter(Animal.player_id == player_id, Animal.sick_since.isnot(None))
                .count()
            )

    def test_an_outbreak_sickens_a_share_of_a_crowded_locality(self, db, player, monkeypatch):
        with get_session() as session:
            row = self._stock_zoo(session, player, 10)
            row.outbreak_checked_at = utcnow() - timedelta(days=10)
            session.commit()

        monkeypatch.setattr(income.random, "random", lambda: 0.0)  # force the roll to fire
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            income.sync_player_income(session, row)
            session.commit()

        # 30% of the 10-animal pool, rounded up.
        assert self._sick_count(player) == 3

    def test_the_first_sync_only_sets_the_anchor(self, db, player, monkeypatch):
        with get_session() as session:
            row = self._stock_zoo(session, player, 10)
            row.outbreak_checked_at = None  # never checked
            session.commit()

        monkeypatch.setattr(income.random, "random", lambda: 0.0)  # would fire if it rolled
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            income.sync_player_income(session, row)
            assert row.outbreak_checked_at is not None
            session.commit()

        assert self._sick_count(player) == 0

    def test_a_small_zoo_is_spared(self, db, player, monkeypatch):
        with get_session() as session:
            row = self._stock_zoo(session, player, 5)  # below OUTBREAK_MIN_HEALTHY
            row.outbreak_checked_at = utcnow() - timedelta(days=10)
            session.commit()

        monkeypatch.setattr(income.random, "random", lambda: 0.0)
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            income.sync_player_income(session, row)
            session.commit()

        assert self._sick_count(player) == 0
