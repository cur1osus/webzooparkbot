from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from api.app.models.enums import GeneLevel, HabitatType


Money = Decimal


def money(value: str | int | Decimal) -> Money:
    raw = value if isinstance(value, Decimal) else Decimal(str(value))
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ratio(value: str | int | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class ExpeditionBalance:
    duration: timedelta
    poor_probability: int
    normal_probability: int
    good_probability: int


GAME_TZ_OFFSET = timedelta(hours=3)
SEASON_LENGTH_DAYS = 30
STARTING_COINS = money("1200")

# The GDD omits exact economy prices; these values are centralized for tuning.
BASE_PACK_PRICE = money("120")
PACK_PRICE_GROWTH = ratio("1.5")
BASE_HABITAT_UNLOCK_PRICE = money("500")
HABITAT_PRICE_GROWTH = ratio("1.5")
BASE_ANIMAL_INCOME_PER_HOUR = money("24")

SURVIVAL_INCOME_MULTIPLIERS: dict[GeneLevel, Decimal] = {
    GeneLevel.LOW: ratio("0.7"),
    GeneLevel.MEDIUM: ratio("1.0"),
    GeneLevel.HIGH: ratio("1.3"),
}

APPEARANCE_INCOME_MULTIPLIERS: dict[GeneLevel, Decimal] = {
    GeneLevel.LOW: ratio("0.6"),
    GeneLevel.MEDIUM: ratio("1.0"),
    GeneLevel.HIGH: ratio("1.5"),
}

SIZE_INCOME_MULTIPLIERS: dict[GeneLevel, Decimal] = {
    GeneLevel.LOW: ratio("0.8"),
    GeneLevel.MEDIUM: ratio("1.0"),
    GeneLevel.HIGH: ratio("1.4"),
}

TERRAIN_MATCH_MULTIPLIER = ratio("1.5")

SURVIVAL_LIFESPAN_DAYS: dict[GeneLevel, int] = {
    GeneLevel.LOW: 4,
    GeneLevel.MEDIUM: 8,
    GeneLevel.HIGH: 15,
}

BREEDING_SUCCESS_CHANCES: dict[tuple[GeneLevel, GeneLevel], Decimal] = {
    (GeneLevel.LOW, GeneLevel.LOW): ratio("0.30"),
    (GeneLevel.LOW, GeneLevel.MEDIUM): ratio("0.45"),
    (GeneLevel.MEDIUM, GeneLevel.LOW): ratio("0.45"),
    (GeneLevel.MEDIUM, GeneLevel.MEDIUM): ratio("0.60"),
    (GeneLevel.MEDIUM, GeneLevel.HIGH): ratio("0.75"),
    (GeneLevel.HIGH, GeneLevel.MEDIUM): ratio("0.75"),
    (GeneLevel.HIGH, GeneLevel.HIGH): ratio("0.90"),
    (GeneLevel.LOW, GeneLevel.HIGH): ratio("0.45"),
    (GeneLevel.HIGH, GeneLevel.LOW): ratio("0.45"),
}

GENE_ROLL_DISTRIBUTION: tuple[tuple[GeneLevel, int], ...] = (
    (GeneLevel.LOW, 40),
    (GeneLevel.MEDIUM, 40),
    (GeneLevel.HIGH, 20),
)

EXPEDITION_BALANCE: dict[HabitatType, ExpeditionBalance] = {
    HabitatType.FIELDS: ExpeditionBalance(timedelta(hours=1), 25, 45, 30),
    HabitatType.DESERT: ExpeditionBalance(timedelta(hours=2), 20, 45, 35),
    HabitatType.FOREST: ExpeditionBalance(timedelta(hours=2, minutes=30), 20, 45, 35),
    HabitatType.MOUNTAINS: ExpeditionBalance(timedelta(hours=3), 15, 45, 40),
    HabitatType.ANTARCTICA: ExpeditionBalance(timedelta(hours=4), 10, 45, 45),
}

GENE_STRENGTH: dict[GeneLevel, int] = {
    GeneLevel.LOW: 1,
    GeneLevel.MEDIUM: 2,
    GeneLevel.HIGH: 3,
}

EXPEDITION_POWER_WEIGHTS = {
    "size": 3,
    "survival": 2,
    "appearance": 1,
}
