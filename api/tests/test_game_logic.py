from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.app.core.errors import AppError
from api.app.db.base import Base
from api.app.models.enums import AnimalOriginType, AnimalStatus, GeneLevel, HabitatType
from api.app.models.habitat import PlayerHabitat
from api.app.models.player import Player
from api.app.models.player_season import PlayerSeason
from api.app.models.season import Season
from api.app.services import breeding_service, expedition_service, profile_service
from api.app.services.logic import (
    create_animal,
    habitat_unlock_price,
    inherit_gene,
    next_paid_pack_price,
    to_storage_datetime,
)


UTC = timezone.utc


class _FixedRandom:
    def __init__(self, value: float) -> None:
        self._value = value

    def random(self) -> float:
        return self._value


class GameLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)
        self.now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _session(self) -> Session:
        return self.Session()

    def _create_profile(self, db: Session) -> tuple[Player, PlayerSeason]:
        season = Season(
            ordinal=1,
            starts_at=to_storage_datetime(self.now - timedelta(days=1)),
            ends_at=to_storage_datetime(self.now + timedelta(days=29)),
        )
        player = Player(telegram_id=123456, nickname="tester")
        profile = PlayerSeason(
            player=player,
            season=season,
            balance_coins=Decimal("0.00"),
            last_income_at=to_storage_datetime(self.now),
        )
        db.add_all([season, player, profile])
        db.flush()
        return player, profile

    def _add_habitat(self, db: Session, profile: PlayerSeason, terrain_type: HabitatType) -> PlayerHabitat:
        habitat = PlayerHabitat(
            player_season=profile,
            terrain_type=terrain_type,
            unlock_order=len(profile.habitats) + 1,
            purchase_price=Decimal("0.00"),
            unlocked_at=to_storage_datetime(self.now),
        )
        db.add(habitat)
        db.flush()
        return habitat

    def _add_animal(
        self,
        db: Session,
        profile: PlayerSeason,
        habitat: PlayerHabitat,
        *,
        breeding_gene: GeneLevel = GeneLevel.MEDIUM,
        dies_at: datetime | None = None,
    ):
        animal = create_animal(
            player_season=profile,
            now=self.now,
            origin_type=AnimalOriginType.PACK,
            survival_gene=GeneLevel.MEDIUM,
            breeding_gene=breeding_gene,
            appearance_gene=GeneLevel.MEDIUM,
            size_gene=GeneLevel.MEDIUM,
            habitat_preference=habitat.terrain_type,
        )
        animal.current_habitat = habitat
        if dies_at is not None:
            animal.dies_at = to_storage_datetime(dies_at)
        db.add(animal)
        db.flush()
        return animal

    def test_paid_pack_price_progression(self) -> None:
        self.assertEqual(next_paid_pack_price(0), Decimal("120.00"))
        self.assertEqual(next_paid_pack_price(1), Decimal("180.00"))
        self.assertEqual(next_paid_pack_price(2), Decimal("270.00"))

    def test_habitat_unlock_price_progression(self) -> None:
        self.assertEqual(habitat_unlock_price(1), Decimal("500.00"))
        self.assertEqual(habitat_unlock_price(2), Decimal("750.00"))
        self.assertEqual(habitat_unlock_price(3), Decimal("1125.00"))

    def test_inherit_gene_respects_60_40_rule(self) -> None:
        self.assertEqual(
            inherit_gene(GeneLevel.LOW, GeneLevel.HIGH, _FixedRandom(0.20)),
            GeneLevel.LOW,
        )
        self.assertEqual(
            inherit_gene(GeneLevel.LOW, GeneLevel.HIGH, _FixedRandom(0.80)),
            GeneLevel.HIGH,
        )

    def test_breeding_is_limited_to_once_per_day(self) -> None:
        with self._session() as db:
            _, profile = self._create_profile(db)
            habitat = self._add_habitat(db, profile, HabitatType.FIELDS)
            first = self._add_animal(db, profile, habitat)
            second = self._add_animal(db, profile, habitat)

            breeding_service.breed_animals(db, profile, first.id, second.id, self.now)

            with self.assertRaises(AppError) as ctx:
                breeding_service.breed_animals(db, profile, first.id, second.id, self.now)

            self.assertEqual(ctx.exception.status_code, 409)

    def test_expedition_resolution_restores_party_and_grants_capture(self) -> None:
        with self._session() as db:
            _, profile = self._create_profile(db)
            habitat = self._add_habitat(db, profile, HabitatType.FIELDS)
            party = [self._add_animal(db, profile, habitat) for _ in range(3)]

            expedition = expedition_service.start_expedition(
                db,
                profile,
                HabitatType.FIELDS,
                [animal.id for animal in party],
                self.now,
            )
            self.assertTrue(all(animal.status == AnimalStatus.ON_EXPEDITION for animal in party))

            weak_wild = create_animal(
                player_season=profile,
                now=self.now + timedelta(hours=1),
                origin_type=AnimalOriginType.EXPEDITION,
                survival_gene=GeneLevel.LOW,
                breeding_gene=GeneLevel.LOW,
                appearance_gene=GeneLevel.LOW,
                size_gene=GeneLevel.LOW,
                habitat_preference=HabitatType.FIELDS,
            )

            with patch("api.app.services.expedition_service.create_expedition_animal", return_value=weak_wild):
                resolved = expedition_service.resolve_expedition(
                    db,
                    profile,
                    expedition.id,
                    self.now + timedelta(hours=2),
                )

            self.assertEqual(resolved.outcome.value, "success")
            self.assertIsNotNone(resolved.captured_animal_id)
            self.assertTrue(all(animal.status == AnimalStatus.ACTIVE for animal in party))

    def test_lazy_income_stops_after_animal_death(self) -> None:
        with self._session() as db:
            _, profile = self._create_profile(db)
            profile.last_income_at = to_storage_datetime(self.now)
            habitat = self._add_habitat(db, profile, HabitatType.FIELDS)
            animal = self._add_animal(db, profile, habitat, dies_at=self.now + timedelta(hours=1))

            profile_service.sync_profile_state(db, profile, self.now + timedelta(hours=2))

            self.assertEqual(profile.balance_coins, Decimal("36.00"))
            self.assertEqual(animal.status, AnimalStatus.DEAD)

    def test_lazy_income_resumes_after_expedition_resolution(self) -> None:
        with self._session() as db:
            _, profile = self._create_profile(db)
            profile.last_income_at = to_storage_datetime(self.now)
            habitat = self._add_habitat(db, profile, HabitatType.FIELDS)
            party = [self._add_animal(db, profile, habitat) for _ in range(3)]

            expedition = expedition_service.start_expedition(
                db,
                profile,
                HabitatType.FIELDS,
                [animal.id for animal in party],
                self.now,
            )

            weak_wild = create_animal(
                player_season=profile,
                now=self.now + timedelta(hours=1),
                origin_type=AnimalOriginType.EXPEDITION,
                survival_gene=GeneLevel.LOW,
                breeding_gene=GeneLevel.LOW,
                appearance_gene=GeneLevel.LOW,
                size_gene=GeneLevel.LOW,
                habitat_preference=HabitatType.FIELDS,
            )

            with patch("api.app.services.expedition_service.create_expedition_animal", return_value=weak_wild):
                profile_service.sync_profile_state(db, profile, self.now + timedelta(hours=2))

            self.assertEqual(expedition.outcome.value, "success")
            self.assertEqual(profile.balance_coins, Decimal("108.00"))


if __name__ == "__main__":
    unittest.main()
