from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.app.models.animal import Animal
from api.app.models.breeding import BreedingAttempt
from api.app.models.enums import AnimalStatus
from api.app.models.expedition import Expedition
from api.app.models.pack import PackOpening
from api.app.models.player_season import PlayerSeason
from api.app.schemas.game import (
    AnimalSummary,
    BreedingAttemptSummary,
    ExpeditionSummary,
    HabitatSummary,
    PackOpeningSummary,
    PackStateSummary,
    ProfileResponse,
    SeasonSummary,
)
from api.app.services.expedition_service import active_expedition
from api.app.services.logic import (
    animal_combat_power,
    animal_income_per_hour,
    current_income_per_hour,
    current_season_day,
    ensure_utc,
    money_str,
    remaining_life_seconds,
    seconds_until_season_end,
)
from api.app.services.pack_service import get_pack_state
from api.app.services.profile_service import locked_habitats


def serialize_habitat(profile: PlayerSeason, habitat) -> HabitatSummary:
    resident_count = sum(
        1
        for animal in profile.animals
        if animal.current_habitat_id == habitat.id and animal.status != AnimalStatus.DEAD
    )
    return HabitatSummary(
        id=habitat.id,
        terrain_type=habitat.terrain_type,
        unlock_order=habitat.unlock_order,
        purchase_price=money_str(habitat.purchase_price),
        resident_count=resident_count,
    )


def serialize_animal(animal: Animal, now: datetime) -> AnimalSummary:
    current_habitat_type = animal.current_habitat.terrain_type if animal.current_habitat else None
    return AnimalSummary(
        id=animal.id,
        status=animal.status.value,
        survival_gene=animal.survival_gene.value,
        breeding_gene=animal.breeding_gene.value,
        appearance_gene=animal.appearance_gene.value,
        size_gene=animal.size_gene.value,
        habitat_preference=animal.habitat_preference,
        current_habitat_id=animal.current_habitat_id,
        current_habitat_type=current_habitat_type,
        income_per_hour=money_str(animal_income_per_hour(animal)),
        combat_power=animal_combat_power(animal),
        can_breed_today=animal.last_breeding_day != current_season_day(animal.player_season.season, now),
        born_at=ensure_utc(animal.born_at),
        dies_at=ensure_utc(animal.dies_at),
        died_at=ensure_utc(animal.died_at) if animal.died_at else None,
        remaining_life_seconds=remaining_life_seconds(animal, now),
        parent_one_id=animal.parent_one_id,
        parent_two_id=animal.parent_two_id,
        origin_type=animal.origin_type.value,
    )


def serialize_pack_state(db: Session, profile: PlayerSeason, now: datetime) -> PackStateSummary:
    state = get_pack_state(db, profile, now)
    return PackStateSummary(
        season_day=state["season_day"],
        free_pack_available=state["free_pack_available"],
        paid_packs_opened_today=state["paid_packs_opened_today"],
        next_paid_pack_price=money_str(state["next_paid_pack_price"]),
    )


def serialize_pack_opening(opening: PackOpening, now: datetime) -> PackOpeningSummary:
    return PackOpeningSummary(
        id=opening.id,
        season_day=opening.season_day,
        opening_type=opening.opening_type,
        price_paid=money_str(opening.price_paid),
        opened_at=ensure_utc(opening.opened_at),
        reward_animal=serialize_animal(opening.reward_animal, now),
    )


def serialize_breeding_attempt(attempt: BreedingAttempt) -> BreedingAttemptSummary:
    return BreedingAttemptSummary(
        id=attempt.id,
        season_day=attempt.season_day,
        first_parent_id=attempt.first_parent_id,
        second_parent_id=attempt.second_parent_id,
        success_probability=format(attempt.success_probability, "f"),
        was_successful=attempt.was_successful,
        child_animal_id=attempt.child_animal_id,
        attempted_at=ensure_utc(attempt.attempted_at),
    )


def serialize_expedition(expedition: Expedition) -> ExpeditionSummary:
    return ExpeditionSummary(
        id=expedition.id,
        target_terrain_type=expedition.target_terrain_type,
        outcome=expedition.outcome,
        started_at=ensure_utc(expedition.started_at),
        resolves_at=ensure_utc(expedition.resolves_at),
        resolved_at=ensure_utc(expedition.resolved_at) if expedition.resolved_at else None,
        party_power=expedition.party_power,
        wild_power=expedition.wild_power,
        captured_animal_id=expedition.captured_animal_id,
        lost_animal_id=expedition.lost_animal_id,
        party_member_ids=[member.animal_id for member in expedition.party_members],
        wild_survival_gene=expedition.wild_survival_gene.value if expedition.wild_survival_gene else None,
        wild_breeding_gene=expedition.wild_breeding_gene.value if expedition.wild_breeding_gene else None,
        wild_appearance_gene=expedition.wild_appearance_gene.value if expedition.wild_appearance_gene else None,
        wild_size_gene=expedition.wild_size_gene.value if expedition.wild_size_gene else None,
    )


def _recent_pack_openings(db: Session, profile: PlayerSeason):
    return list(
        db.scalars(
            select(PackOpening)
            .options(selectinload(PackOpening.reward_animal).selectinload(Animal.current_habitat))
            .where(PackOpening.player_season_id == profile.id)
            .order_by(PackOpening.opened_at.desc())
            .limit(10)
        )
    )


def _recent_breeding_attempts(db: Session, profile: PlayerSeason):
    return list(
        db.scalars(
            select(BreedingAttempt)
            .where(BreedingAttempt.player_season_id == profile.id)
            .order_by(BreedingAttempt.attempted_at.desc())
            .limit(10)
        )
    )


def _recent_expeditions(db: Session, profile: PlayerSeason):
    return list(
        db.scalars(
            select(Expedition)
            .options(selectinload(Expedition.party_members))
            .where(Expedition.player_season_id == profile.id)
            .order_by(Expedition.started_at.desc())
            .limit(10)
        )
    )


def build_profile_response(db: Session, profile: PlayerSeason, now: datetime) -> ProfileResponse:
    active = active_expedition(db, profile)
    habitats = sorted(profile.habitats, key=lambda habitat: habitat.unlock_order)
    animals = sorted(
        profile.animals,
        key=lambda animal: (animal.status == AnimalStatus.DEAD, animal.dies_at, animal.id),
    )
    season = profile.season

    return ProfileResponse(
        player_id=profile.player.id,
        telegram_id=profile.player.telegram_id,
        nickname=profile.player.nickname,
        season=SeasonSummary(
            id=season.id,
            ordinal=season.ordinal,
            starts_at=ensure_utc(season.starts_at),
            ends_at=ensure_utc(season.ends_at),
            current_day=current_season_day(season, now),
            seconds_until_end=seconds_until_season_end(season, now),
        ),
        balance_coins=money_str(profile.balance_coins),
        current_income_per_hour=money_str(current_income_per_hour(profile)),
        habitats=[serialize_habitat(profile, habitat) for habitat in habitats],
        animals=[serialize_animal(animal, now) for animal in animals],
        pack_state=serialize_pack_state(db, profile, now),
        active_expedition=serialize_expedition(active) if active else None,
        recent_expeditions=[serialize_expedition(expedition) for expedition in _recent_expeditions(db, profile)],
        recent_breeding_attempts=[serialize_breeding_attempt(attempt) for attempt in _recent_breeding_attempts(db, profile)],
        recent_pack_openings=[serialize_pack_opening(opening, now) for opening in _recent_pack_openings(db, profile)],
        locked_habitat_types=locked_habitats(profile),
    )
