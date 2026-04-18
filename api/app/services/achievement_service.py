from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from api.app.core.errors import AppError
from api.app.models.achievement_unlock import AchievementUnlock
from api.app.models.animal import Animal
from api.app.models.enums import AnimalOriginType, AnimalStatus, ExpeditionOutcome, GeneLevel
from api.app.models.player import Player
from api.app.models.player_season import PlayerSeason
from api.app.services.logic import current_income_per_hour, ensure_utc
from api.app.services.profile_service import ensure_player_profile as ensure_player_profile_row


@dataclass(frozen=True)
class AchievementDefinition:
    id: str
    name: str
    description: str
    order: int
    cosmetic_id: str
    metric_label: str
    target_value: int


@dataclass(frozen=True)
class AchievementState:
    definition: AchievementDefinition
    progress: float
    unlocked: bool
    unlocked_at: datetime | None


ACHIEVEMENT_DEFINITIONS = (
    AchievementDefinition(
        id="great_recruiter",
        name="Великий рекрутер",
        description="Приведи в менagerie трех животных из экспедиций.",
        order=1,
        cosmetic_id="cosmetic_great_recruiter",
        metric_label="expedition_recruits",
        target_value=3,
    ),
    AchievementDefinition(
        id="clan_pillar",
        name="Опора стаи",
        description="Успешно заверши три экспедиции полной партией.",
        order=2,
        cosmetic_id="cosmetic_clan_pillar",
        metric_label="full_party_successes",
        target_value=3,
    ),
    AchievementDefinition(
        id="empire_of_species",
        name="Империя видов",
        description="Собери животных из всех пяти природных биомов.",
        order=3,
        cosmetic_id="cosmetic_empire_of_species",
        metric_label="habitat_variety",
        target_value=5,
    ),
    AchievementDefinition(
        id="crystal_forge",
        name="Кристальная кузня",
        description="Проведи пять успешных скрещиваний.",
        order=4,
        cosmetic_id="cosmetic_crystal_forge",
        metric_label="successful_breedings",
        target_value=5,
    ),
    AchievementDefinition(
        id="income_throne",
        name="Трон дохода",
        description="Достигни дохода в 1 000 монет в час.",
        order=5,
        cosmetic_id="cosmetic_income_throne",
        metric_label="income_per_hour",
        target_value=1000,
    ),
    AchievementDefinition(
        id="architect_of_infinity",
        name="Архитектор бесконечности",
        description="Открой все доступные местности сезона.",
        order=6,
        cosmetic_id="cosmetic_architect_of_infinity",
        metric_label="unlocked_habitats",
        target_value=5,
    ),
    AchievementDefinition(
        id="rising_legend",
        name="Восходящая легенда",
        description="Вырасти животное минимум с тремя сильными генами.",
        order=7,
        cosmetic_id="cosmetic_rising_legend",
        metric_label="high_gene_animals",
        target_value=1,
    ),
)

DEFINITION_BY_ID = {definition.id: definition for definition in ACHIEVEMENT_DEFINITIONS}


def _progress_ratio(value: int, target: int) -> float:
    if target <= 0:
        return 1.0
    return min(1.0, max(0.0, value / target))


def _high_gene_count(animal: Animal) -> int:
    return sum(
        1
        for gene in (animal.survival_gene, animal.breeding_gene, animal.appearance_gene, animal.size_gene)
        if gene == GeneLevel.HIGH
    )


def _metric_value(profile: PlayerSeason, metric_label: str) -> int:
    active_animals = [animal for animal in profile.animals if animal.status != AnimalStatus.DEAD]

    if metric_label == "expedition_recruits":
        return sum(1 for animal in profile.animals if animal.origin_type == AnimalOriginType.EXPEDITION)
    if metric_label == "full_party_successes":
        return sum(
            1
            for expedition in profile.expeditions
            if expedition.outcome == ExpeditionOutcome.SUCCESS and len(expedition.party_members) >= 3
        )
    if metric_label == "habitat_variety":
        return len({animal.habitat_preference for animal in active_animals})
    if metric_label == "successful_breedings":
        return sum(1 for attempt in profile.breeding_attempts if attempt.was_successful)
    if metric_label == "income_per_hour":
        return int(current_income_per_hour(profile))
    if metric_label == "unlocked_habitats":
        return len(profile.habitats)
    if metric_label == "high_gene_animals":
        return sum(1 for animal in active_animals if _high_gene_count(animal) >= 3)
    raise ValueError(f"Unsupported achievement metric: {metric_label}")


def _unlock_map(player: Player) -> dict[str, AchievementUnlock]:
    return {unlock.achievement_id: unlock for unlock in player.achievement_unlocks}


def sync_achievements(db: Session, profile: PlayerSeason, now: datetime) -> tuple[list[AchievementState], list[str]]:
    unlocked = _unlock_map(profile.player)
    newly_unlocked: list[str] = []
    states: list[AchievementState] = []

    for definition in ACHIEVEMENT_DEFINITIONS:
        value = _metric_value(profile, definition.metric_label)
        progress = _progress_ratio(value, definition.target_value)
        unlock = unlocked.get(definition.id)
        is_unlocked = unlock is not None or value >= definition.target_value

        if unlock is None and value >= definition.target_value:
            unlock = AchievementUnlock(
                player=profile.player,
                achievement_id=definition.id,
                unlocked_at=ensure_utc(now),
            )
            db.add(unlock)
            db.flush()
            unlocked[definition.id] = unlock
            newly_unlocked.append(definition.id)

        states.append(
            AchievementState(
                definition=definition,
                progress=progress,
                unlocked=is_unlocked,
                unlocked_at=ensure_utc(unlock.unlocked_at) if unlock is not None else None,
            )
        )

    return states, newly_unlocked


def get_active_cosmetic_id(profile: PlayerSeason) -> str | None:
    return profile.player.profile.active_achievement_cosmetic_id if profile.player.profile else None


def equip_cosmetic(db: Session, profile: PlayerSeason, cosmetic_id: str | None) -> str | None:
    preferences = ensure_player_profile_row(db, profile.player)
    if cosmetic_id is None:
        preferences.active_achievement_cosmetic_id = None
        db.flush()
        return None

    matching_definition = next(
        (definition for definition in ACHIEVEMENT_DEFINITIONS if definition.cosmetic_id == cosmetic_id),
        None,
    )
    if matching_definition is None:
        raise AppError("Unknown achievement cosmetic", status_code=404)

    unlocked_ids = {unlock.achievement_id for unlock in profile.player.achievement_unlocks}
    if matching_definition.id not in unlocked_ids:
        raise AppError("Achievement cosmetic is not unlocked", status_code=409)

    preferences.active_achievement_cosmetic_id = cosmetic_id
    db.flush()
    return cosmetic_id
