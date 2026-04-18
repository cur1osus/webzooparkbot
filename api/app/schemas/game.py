from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from api.app.models.enums import ExpeditionOutcome, HabitatType, PackOpeningType


class RegisterRequest(BaseModel):
    nickname: str = Field(min_length=3, max_length=64)


class UnlockHabitatRequest(BaseModel):
    terrain_type: HabitatType


class AssignAnimalHabitatRequest(BaseModel):
    habitat_id: int


class BreedAnimalsRequest(BaseModel):
    first_parent_id: str
    second_parent_id: str


class StartExpeditionRequest(BaseModel):
    target_terrain_type: HabitatType
    animal_ids: list[str] = Field(min_length=3, max_length=5)


class SeasonSummary(BaseModel):
    id: int
    ordinal: int
    starts_at: datetime
    ends_at: datetime
    current_day: int
    seconds_until_end: int


class HabitatSummary(BaseModel):
    id: int
    terrain_type: HabitatType
    unlock_order: int
    purchase_price: str
    resident_count: int


class AnimalSummary(BaseModel):
    id: str
    status: str
    survival_gene: str
    breeding_gene: str
    appearance_gene: str
    size_gene: str
    habitat_preference: HabitatType
    current_habitat_id: int | None
    current_habitat_type: HabitatType | None
    income_per_hour: str
    combat_power: int
    can_breed_today: bool
    born_at: datetime
    dies_at: datetime
    died_at: datetime | None
    remaining_life_seconds: int
    parent_one_id: str | None
    parent_two_id: str | None
    origin_type: str


class PackStateSummary(BaseModel):
    season_day: int
    free_pack_available: bool
    paid_packs_opened_today: int
    next_paid_pack_price: str


class PackOpeningSummary(BaseModel):
    id: int
    season_day: int
    opening_type: PackOpeningType
    price_paid: str
    opened_at: datetime
    reward_animal: AnimalSummary


class BreedingAttemptSummary(BaseModel):
    id: int
    season_day: int
    first_parent_id: str
    second_parent_id: str
    success_probability: str
    was_successful: bool
    child_animal_id: str | None
    attempted_at: datetime


class ExpeditionSummary(BaseModel):
    id: int
    target_terrain_type: HabitatType
    outcome: ExpeditionOutcome
    started_at: datetime
    resolves_at: datetime
    resolved_at: datetime | None
    party_power: int | None
    wild_power: int | None
    captured_animal_id: str | None
    lost_animal_id: str | None
    party_member_ids: list[str]
    wild_survival_gene: str | None
    wild_breeding_gene: str | None
    wild_appearance_gene: str | None
    wild_size_gene: str | None


class ProfileResponse(BaseModel):
    player_id: int
    telegram_id: int
    nickname: str
    season: SeasonSummary
    balance_coins: str
    current_income_per_hour: str
    habitats: list[HabitatSummary]
    animals: list[AnimalSummary]
    pack_state: PackStateSummary
    active_expedition: ExpeditionSummary | None
    recent_expeditions: list[ExpeditionSummary]
    recent_breeding_attempts: list[BreedingAttemptSummary]
    recent_pack_openings: list[PackOpeningSummary]
    locked_habitat_types: list[HabitatType]


class PackOpenResponse(BaseModel):
    opening: PackOpeningSummary
    profile: ProfileResponse


class HabitatUnlockResponse(BaseModel):
    habitat: HabitatSummary
    profile: ProfileResponse


class AnimalAssignmentResponse(BaseModel):
    animal: AnimalSummary
    profile: ProfileResponse


class BreedAnimalsResponse(BaseModel):
    attempt: BreedingAttemptSummary
    profile: ProfileResponse


class ExpeditionStartResponse(BaseModel):
    expedition: ExpeditionSummary
    profile: ProfileResponse


class ExpeditionResolveResponse(BaseModel):
    expedition: ExpeditionSummary
    profile: ProfileResponse


class ConfigResponse(BaseModel):
    season_length_days: int
    base_pack_price: str
    pack_price_growth: str
    base_habitat_unlock_price: str
    starting_coins: str
    base_animal_income_per_hour: str


class HealthResponse(BaseModel):
    ok: bool
