from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random

from api.app.domain.balance import (
    APPEARANCE_INCOME_MULTIPLIERS,
    BASE_ANIMAL_INCOME_PER_HOUR,
    BASE_HABITAT_UNLOCK_PRICE,
    BASE_PACK_PRICE,
    BREEDING_SUCCESS_CHANCES,
    EXPEDITION_BALANCE,
    EXPEDITION_POWER_WEIGHTS,
    GENE_ROLL_DISTRIBUTION,
    GENE_STRENGTH,
    HABITAT_PRICE_GROWTH,
    PACK_PRICE_GROWTH,
    SEASON_LENGTH_DAYS,
    SIZE_INCOME_MULTIPLIERS,
    STARTING_COINS,
    SURVIVAL_INCOME_MULTIPLIERS,
    SURVIVAL_LIFESPAN_DAYS,
    TERRAIN_MATCH_MULTIPLIER,
    money,
)
from api.app.models.animal import Animal
from api.app.models.enums import AnimalOriginType, AnimalStatus, GeneLevel, HabitatType
from api.app.models.player_season import PlayerSeason
from api.app.models.season import Season


UTC = timezone.utc
GENE_ORDER = [GeneLevel.LOW, GeneLevel.MEDIUM, GeneLevel.HIGH]


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_storage_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def current_season_day(season: Season, now: datetime) -> int:
    start = ensure_utc(season.starts_at)
    delta = ensure_utc(now) - start
    if delta.total_seconds() <= 0:
        return 1
    return min(SEASON_LENGTH_DAYS, delta.days + 1)


def seconds_until_season_end(season: Season, now: datetime) -> int:
    end = ensure_utc(season.ends_at)
    return max(0, int((end - ensure_utc(now)).total_seconds()))


def next_season_bounds(previous: Season | None, now: datetime) -> tuple[int, datetime, datetime]:
    now_utc = ensure_utc(now)
    if previous is None:
        starts_at = now_utc
        ordinal = 1
    else:
        starts_at = max(ensure_utc(previous.ends_at), now_utc)
        ordinal = previous.ordinal + 1
    ends_at = starts_at + timedelta(days=SEASON_LENGTH_DAYS)
    return ordinal, to_storage_datetime(starts_at), to_storage_datetime(ends_at)


def money_str(value: Decimal) -> str:
    return format(money(value), "f")


def habitat_unlock_price(existing_unlocked_count: int) -> Decimal:
    bought_habitats = max(0, existing_unlocked_count - 1)
    return money(BASE_HABITAT_UNLOCK_PRICE * (HABITAT_PRICE_GROWTH ** bought_habitats))


def next_paid_pack_price(paid_packs_opened_today: int) -> Decimal:
    return money(BASE_PACK_PRICE * (PACK_PRICE_GROWTH ** paid_packs_opened_today))


def random_habitat(rng: random.Random) -> HabitatType:
    return rng.choice(list(HabitatType))


def weighted_gene_roll(weights: tuple[tuple[GeneLevel, int], ...], rng: random.Random) -> GeneLevel:
    threshold = rng.randint(1, sum(weight for _, weight in weights))
    cursor = 0
    for gene, weight in weights:
        cursor += weight
        if threshold <= cursor:
            return gene
    return weights[-1][0]


def roll_standard_gene(rng: random.Random) -> GeneLevel:
    return weighted_gene_roll(GENE_ROLL_DISTRIBUTION, rng)


def roll_expedition_gene(terrain_type: HabitatType, rng: random.Random) -> GeneLevel:
    balance = EXPEDITION_BALANCE[terrain_type]
    weights = (
        (GeneLevel.LOW, balance.poor_probability),
        (GeneLevel.MEDIUM, balance.normal_probability),
        (GeneLevel.HIGH, balance.good_probability),
    )
    return weighted_gene_roll(weights, rng)


def animal_lifespan_days(survival_gene: GeneLevel) -> int:
    return SURVIVAL_LIFESPAN_DAYS[survival_gene]


def animal_combat_power(animal: Animal) -> int:
    return (
        GENE_STRENGTH[animal.size_gene] * EXPEDITION_POWER_WEIGHTS["size"]
        + GENE_STRENGTH[animal.survival_gene] * EXPEDITION_POWER_WEIGHTS["survival"]
        + GENE_STRENGTH[animal.appearance_gene] * EXPEDITION_POWER_WEIGHTS["appearance"]
    )


def party_combat_power(animals: list[Animal]) -> int:
    return sum(animal_combat_power(animal) for animal in animals)


def animal_income_per_hour(animal: Animal) -> Decimal:
    if animal.status != AnimalStatus.ACTIVE or animal.current_habitat is None:
        return money("0")

    income = BASE_ANIMAL_INCOME_PER_HOUR
    income *= SURVIVAL_INCOME_MULTIPLIERS[animal.survival_gene]
    income *= APPEARANCE_INCOME_MULTIPLIERS[animal.appearance_gene]
    income *= SIZE_INCOME_MULTIPLIERS[animal.size_gene]
    if animal.current_habitat.terrain_type == animal.habitat_preference:
        income *= TERRAIN_MATCH_MULTIPLIER
    return money(income)


def breeding_success_probability(first_gene: GeneLevel, second_gene: GeneLevel) -> Decimal:
    return BREEDING_SUCCESS_CHANCES[(first_gene, second_gene)]


def inherit_gene(first_gene: GeneLevel, second_gene: GeneLevel, rng: random.Random) -> GeneLevel:
    if first_gene == second_gene:
        return first_gene
    first_rank = GENE_ORDER.index(first_gene)
    second_rank = GENE_ORDER.index(second_gene)
    worse = first_gene if first_rank < second_rank else second_gene
    better = second_gene if worse == first_gene else first_gene
    return worse if rng.random() < 0.6 else better


def create_animal(
    *,
    player_season: PlayerSeason,
    now: datetime,
    origin_type: AnimalOriginType,
    survival_gene: GeneLevel,
    breeding_gene: GeneLevel,
    appearance_gene: GeneLevel,
    size_gene: GeneLevel,
    habitat_preference: HabitatType,
    parent_one_id: str | None = None,
    parent_two_id: str | None = None,
) -> Animal:
    born_at = ensure_utc(now)
    dies_at = born_at + timedelta(days=animal_lifespan_days(survival_gene))
    return Animal(
        player_season=player_season,
        origin_type=origin_type,
        survival_gene=survival_gene,
        breeding_gene=breeding_gene,
        appearance_gene=appearance_gene,
        size_gene=size_gene,
        habitat_preference=habitat_preference,
        status=AnimalStatus.ACTIVE,
        born_at=to_storage_datetime(born_at),
        dies_at=to_storage_datetime(dies_at),
        parent_one_id=parent_one_id,
        parent_two_id=parent_two_id,
    )


def create_pack_animal(player_season: PlayerSeason, now: datetime, rng: random.Random) -> Animal:
    return create_animal(
        player_season=player_season,
        now=now,
        origin_type=AnimalOriginType.PACK,
        survival_gene=roll_standard_gene(rng),
        breeding_gene=roll_standard_gene(rng),
        appearance_gene=roll_standard_gene(rng),
        size_gene=roll_standard_gene(rng),
        habitat_preference=rng.choice(list(HabitatType)),
    )


def create_expedition_animal(player_season: PlayerSeason, now: datetime, terrain_type: HabitatType, rng: random.Random) -> Animal:
    return create_animal(
        player_season=player_season,
        now=now,
        origin_type=AnimalOriginType.EXPEDITION,
        survival_gene=roll_expedition_gene(terrain_type, rng),
        breeding_gene=roll_expedition_gene(terrain_type, rng),
        appearance_gene=roll_expedition_gene(terrain_type, rng),
        size_gene=roll_expedition_gene(terrain_type, rng),
        habitat_preference=terrain_type,
    )


def create_bred_animal(player_season: PlayerSeason, now: datetime, first_parent: Animal, second_parent: Animal, rng: random.Random) -> Animal:
    return create_animal(
        player_season=player_season,
        now=now,
        origin_type=AnimalOriginType.BREEDING,
        survival_gene=inherit_gene(first_parent.survival_gene, second_parent.survival_gene, rng),
        breeding_gene=inherit_gene(first_parent.breeding_gene, second_parent.breeding_gene, rng),
        appearance_gene=inherit_gene(first_parent.appearance_gene, second_parent.appearance_gene, rng),
        size_gene=inherit_gene(first_parent.size_gene, second_parent.size_gene, rng),
        habitat_preference=rng.choice([first_parent.habitat_preference, second_parent.habitat_preference]),
        parent_one_id=first_parent.id,
        parent_two_id=second_parent.id,
    )


def available_locked_habitats(profile: PlayerSeason) -> list[HabitatType]:
    unlocked = {habitat.terrain_type for habitat in profile.habitats}
    return [terrain for terrain in HabitatType if terrain not in unlocked]


def current_income_per_hour(profile: PlayerSeason) -> Decimal:
    return money(sum((animal_income_per_hour(animal) for animal in profile.animals), Decimal("0")))


def remaining_life_seconds(animal: Animal, now: datetime) -> int:
    if animal.status == AnimalStatus.DEAD:
        return 0
    return max(0, int((ensure_utc(animal.dies_at) - ensure_utc(now)).total_seconds()))


def expedition_duration(terrain_type: HabitatType) -> timedelta:
    return EXPEDITION_BALANCE[terrain_type].duration


def starting_coins() -> Decimal:
    return STARTING_COINS
