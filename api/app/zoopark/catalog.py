"""Static game catalogue and balance constants.

The canonical design is `Merchant's Menagerie GDD v1.0`. Where this file departs from
it, the departure is called out in a comment and the reason given.

Everything here is code, not database rows. The original bot kept these in an EAV
`values` table so an admin panel could edit them; this app has no admin panel, and
untyped strings in a table cannot be reviewed, typed or tested. The only piece of
economy state that genuinely changes at runtime is the bank rate, which lives in the
`bank_rates` table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict, cast

Rarity = Literal["rare", "epic", "mythic", "legendary"]
Habitat = Literal["desert", "mountains", "forest", "fields", "antarctica"]
GeneTier = Literal["low", "medium", "high"]
Currency = Literal["rub", "usd", "paw"]

HABITATS: tuple[Habitat, ...] = ("desert", "mountains", "forest", "fields", "antarctica")
GENE_TIERS: tuple[GeneTier, ...] = ("low", "medium", "high")
CURRENCIES: tuple[Currency, ...] = ("rub", "usd", "paw")
RARITIES: tuple[Rarity, ...] = ("rare", "epic", "mythic", "legendary")

class NicknameColorDef(TypedDict):
    price_paw: int
    animated: bool
    rarity: str


# Profile cosmetics use a fixed server catalogue, so the database never stores CSS from a
# client. Dynamic variants cost more because they are the premium visual signature.
NICKNAME_COLORS: dict[str, NicknameColorDef] = {
    "ivory": {"price_paw": 0, "animated": False, "rarity": "standard"},
    "gold": {"price_paw": 75, "animated": False, "rarity": "standard"},
    "jade": {"price_paw": 75, "animated": False, "rarity": "standard"},
    "lagoon": {"price_paw": 75, "animated": False, "rarity": "standard"},
    "orchid": {"price_paw": 75, "animated": False, "rarity": "standard"},
    "coral": {"price_paw": 75, "animated": False, "rarity": "standard"},
    "aurora": {"price_paw": 250, "animated": True, "rarity": "rare"},
    "embers": {"price_paw": 250, "animated": True, "rarity": "rare"},
    "spectrum": {"price_paw": 350, "animated": True, "rarity": "rare"},
    "neon": {"price_paw": 250, "animated": True, "rarity": "rare"},
    "wave": {"price_paw": 250, "animated": True, "rarity": "rare"},
    "wave-azure": {"price_paw": 250, "animated": True, "rarity": "rare"},
    "wave-violet": {"price_paw": 250, "animated": True, "rarity": "rare"},
    "glitch": {"price_paw": 500, "animated": True, "rarity": "legendary"},
    "glitch-aqua": {"price_paw": 500, "animated": True, "rarity": "legendary"},
    "glitch-lime": {"price_paw": 500, "animated": True, "rarity": "legendary"},
    "glitch-sunset": {"price_paw": 500, "animated": True, "rarity": "legendary"},
    "google": {"price_paw": 700, "animated": True, "rarity": "legendary"},
}


class ProfileFrameDef(TypedDict):
    price_paw: int
    animated: bool
    rarity: str


# Avatar frames wrap the profile badge on the leaderboard and in the player card. Like the
# nickname colours they use a fixed server catalogue; ownership is tracked in the shared
# player_cosmetics table under a "frame:" prefix so ids never collide with colours.
PROFILE_FRAMES: dict[str, ProfileFrameDef] = {
    "none": {"price_paw": 0, "animated": False, "rarity": "standard"},
    "brass": {"price_paw": 120, "animated": False, "rarity": "standard"},
    "jade": {"price_paw": 120, "animated": False, "rarity": "standard"},
    "coral": {"price_paw": 120, "animated": False, "rarity": "standard"},
    "azure": {"price_paw": 120, "animated": False, "rarity": "standard"},
    "aurora": {"price_paw": 320, "animated": True, "rarity": "rare"},
    "ember": {"price_paw": 320, "animated": True, "rarity": "rare"},
    "spectrum": {"price_paw": 480, "animated": True, "rarity": "legendary"},
    "royal": {"price_paw": 480, "animated": True, "rarity": "legendary"},
}


class ProfileWallpaperDef(TypedDict):
    price_paw: int
    animated: bool
    rarity: str


# Profile wallpapers back the identity header on the player card and the home HUD. Same
# server-catalogue pattern as frames; ownership lives in player_cosmetics under a "wall:"
# prefix. The visuals are original CSS/SVG fills, not third-party assets.
PROFILE_WALLPAPERS: dict[str, ProfileWallpaperDef] = {
    "none": {"price_paw": 0, "animated": False, "rarity": "standard"},
    "dusk": {"price_paw": 150, "animated": False, "rarity": "standard"},
    "sunrise": {"price_paw": 150, "animated": False, "rarity": "standard"},
    "meadow": {"price_paw": 150, "animated": False, "rarity": "standard"},
    "ocean": {"price_paw": 150, "animated": False, "rarity": "standard"},
    "bubbles": {"price_paw": 280, "animated": False, "rarity": "rare"},
    "grid": {"price_paw": 280, "animated": False, "rarity": "rare"},
    "paws": {"price_paw": 360, "animated": False, "rarity": "legendary"},
    "stars": {"price_paw": 360, "animated": False, "rarity": "legendary"},
}

# GDD §2: "Среда обитания — равномерно: 20% на каждую из 5 местностей."
# GDD §1: "Низкое: 40%, Среднее: 40%, Высокое: 20%" for each of the four genes.
GENE_ROLL_WEIGHTS: tuple[float, float, float] = (0.40, 0.40, 0.20)

# ─── Species ──────────────────────────────────────────────────────────────────
#
# GDD §3 derives income from genes and habitat. The rarity multiplier below is a small
# economy-facing extension: species rarity matters, but genes still dominate the result.
# The old catalogue carried `price` and `income` columns per species (a leftover from
# the Telegram bot, where animals were bought by the thousand and had no genes); nothing
# read them, and they implied a ladder from a 1 100 ₽ rabbit to a 268 000 000 000 ₽ narwhal
# that the income formula flatly contradicted. They are gone.


class SpeciesDef(TypedDict):
    code: str
    name: str
    emoji: str
    rarity: Rarity


SPECIES: list[SpeciesDef] = [
    {"code": "rabbit", "name": "Кролик", "emoji": "🐇", "rarity": "rare"},
    {"code": "mouse", "name": "Мышь", "emoji": "🐭", "rarity": "rare"},
    {"code": "flamingo", "name": "Фламинго", "emoji": "🦩", "rarity": "rare"},
    {"code": "orca", "name": "Косатка", "emoji": "🐳", "rarity": "rare"},
    {"code": "gibbon", "name": "Гиббон", "emoji": "🐒", "rarity": "rare"},
    {"code": "ferret", "name": "Хорёк", "emoji": "🦦", "rarity": "rare"},
    {"code": "squirrel", "name": "Белка", "emoji": "🐿", "rarity": "rare"},
    {"code": "penguin", "name": "Пингвин", "emoji": "🐧", "rarity": "rare"},
    {"code": "turtle", "name": "Черепаха", "emoji": "🐢", "rarity": "rare"},
    {"code": "parrot", "name": "Попугай", "emoji": "🦜", "rarity": "rare"},
    {"code": "dolphin", "name": "Дельфин", "emoji": "🐬", "rarity": "epic"},
    {"code": "seal", "name": "Тюлень", "emoji": "🦭", "rarity": "epic"},
    {"code": "fox", "name": "Лиса", "emoji": "🦊", "rarity": "epic"},
    {"code": "wolf", "name": "Волк", "emoji": "🐺", "rarity": "epic"},
    {"code": "bear", "name": "Медведь", "emoji": "🐻", "rarity": "epic"},
    {"code": "raccoon", "name": "Енот", "emoji": "🦝", "rarity": "epic"},
    {"code": "panda", "name": "Панда", "emoji": "🐼", "rarity": "epic"},
    {"code": "elephant", "name": "Слон", "emoji": "🐘", "rarity": "epic"},
    {"code": "giraffe", "name": "Жираф", "emoji": "🦒", "rarity": "epic"},
    {"code": "zebra", "name": "Зебра", "emoji": "🦓", "rarity": "epic"},
    {"code": "lion", "name": "Лев", "emoji": "🦁", "rarity": "mythic"},
    {"code": "tiger", "name": "Тигр", "emoji": "🐯", "rarity": "mythic"},
    {"code": "hippo", "name": "Бегемот", "emoji": "🦛", "rarity": "mythic"},
    {"code": "rhino", "name": "Носорог", "emoji": "🦏", "rarity": "mythic"},
    {"code": "camel", "name": "Верблюд", "emoji": "🐪", "rarity": "mythic"},
    {"code": "kangaroo", "name": "Кенгуру", "emoji": "🦘", "rarity": "mythic"},
    {"code": "gorilla", "name": "Горилла", "emoji": "🦍", "rarity": "mythic"},
    {"code": "whale", "name": "Кит", "emoji": "🐋", "rarity": "mythic"},
    {"code": "shark", "name": "Акула", "emoji": "🦈", "rarity": "mythic"},
    {"code": "polar_bear", "name": "Белый медведь", "emoji": "🐻‍❄️", "rarity": "mythic"},
    {"code": "dragon", "name": "Дракон", "emoji": "🐲", "rarity": "legendary"},
    {"code": "unicorn", "name": "Единорог", "emoji": "🦄", "rarity": "legendary"},
    {"code": "phoenix", "name": "Феникс", "emoji": "🔥", "rarity": "legendary"},
    {"code": "kraken", "name": "Кракен", "emoji": "🦑", "rarity": "legendary"},
    {"code": "griffin", "name": "Грифон", "emoji": "🦅", "rarity": "legendary"},
    {"code": "fenec", "name": "Фенек", "emoji": "🦊", "rarity": "legendary"},
    {"code": "mammoth", "name": "Мамонт", "emoji": "🦣", "rarity": "legendary"},
    {"code": "reindeer", "name": "Олень", "emoji": "🦌", "rarity": "legendary"},
    {"code": "peacock", "name": "Павлин", "emoji": "🦚", "rarity": "legendary"},
    {"code": "narwhal", "name": "Нарвал", "emoji": "🐟", "rarity": "legendary"},
]

SPECIES_BY_CODE: dict[str, SpeciesDef] = {s["code"]: s for s in SPECIES}
SPECIES_ID_BY_CODE: dict[str, int] = {s["code"]: index for index, s in enumerate(SPECIES, start=1)}
SPECIES_BY_ID: dict[int, SpeciesDef] = dict(enumerate(SPECIES, start=1))
SPECIES_IDS_BY_RARITY: dict[Rarity, list[int]] = {
    rarity: [i for i, s in SPECIES_BY_ID.items() if s["rarity"] == rarity] for rarity in RARITIES
}

# Species rarity is rolled independently from genes. It defines the species' baseline
# income, while inherited genes and current state refine that baseline.
SPECIES_RARITY_WEIGHTS: dict[Rarity, float] = {
    "rare": 0.55, "epic": 0.30, "mythic": 0.12, "legendary": 0.03,
}

SPECIES_RARITY_INCOME_MULT: dict[Rarity, float] = {
    "rare": 0.8,
    "epic": 1.2,
    "mythic": 1.8,
    "legendary": 2.6,
}

# ─── Genes and income ─────────────────────────────────────────────────────────
#
# GDD §3: Доход = База × М_выживаемость × М_внешность × М_размер × М_местность.
# The `reproduction` gene deliberately has no income multiplier (GDD §9).

# The first economy pass used whole-ruble values that were 100× too large for the
# actual zoo size. Rubles and dollars are now rebased together; PawCoins stay premium
# and keep their original denomination.
BASE_INCOME_RUB_PER_MIN = 50

GENE_INCOME_MULT: dict[str, dict[GeneTier, float]] = {
    "survival": {"low": 0.7, "medium": 1.0, "high": 1.3},
    "appearance": {"low": 0.6, "medium": 1.0, "high": 1.5},
    "size": {"low": 0.8, "medium": 1.0, "high": 1.4},
}

# GDD §5: x1.5 when the animal stands in a locality of its own habitat, x1.0 otherwise.
HABITAT_MATCH_BONUS = 1.5

# GDD §4.
LIFESPAN_DAYS: dict[GeneTier, int] = {"low": 4, "medium": 8, "high": 15}

# GDD §7 (combat): Сила = (Размер × 3) + (Выживаемость × 2) + (Внешний вид × 1).
COMBAT_TIER: dict[GeneTier, int] = {"low": 1, "medium": 2, "high": 3}


def gene_income_mult(survival: GeneTier, appearance: GeneTier, size: GeneTier) -> float:
    """0.336 (all low) … 2.73 (all high). With the habitat bonus the GDD's 12:1 spread."""
    return (
        GENE_INCOME_MULT["survival"][survival]
        * GENE_INCOME_MULT["appearance"][appearance]
        * GENE_INCOME_MULT["size"][size]
    )


def combat_power(survival: GeneTier, appearance: GeneTier, size: GeneTier) -> int:
    return COMBAT_TIER[size] * 3 + COMBAT_TIER[survival] * 2 + COMBAT_TIER[appearance]


def _expected(weights: tuple[float, float, float], values: dict[GeneTier, float]) -> float:
    low, medium, high = weights
    return low * values["low"] + medium * values["medium"] + high * values["high"]


def expected_gene_income_mult(weights: tuple[float, float, float] = GENE_ROLL_WEIGHTS) -> float:
    product = 1.0
    for tiers in GENE_INCOME_MULT.values():
        product *= _expected(weights, tiers)
    return product


def expected_lifespan_minutes(weights: tuple[float, float, float] = GENE_ROLL_WEIGHTS) -> float:
    return _expected(weights, {k: float(v) for k, v in LIFESPAN_DAYS.items()}) * 24 * 60


def lifetime_income_rub(survival: GeneTier, appearance: GeneTier, size: GeneTier) -> int:
    """Everything one animal will ever earn, standing outside its own habitat."""
    per_minute = BASE_INCOME_RUB_PER_MIN * gene_income_mult(survival, appearance, size)
    return int(per_minute * LIFESPAN_DAYS[survival] * 24 * 60)


# ─── Sickness ─────────────────────────────────────────────────────────────────
#
# Not in the GDD, which only has expedition deaths. Carried over from the Telegram bot,
# where a sick animal halves its own income until cured. The web app had it as a flat
# 500 ₽/min penalty, which is meaningless against a 1 680 … 20 475 ₽/min animal.

SICK_INCOME_MULT = 0.5
# Curing costs dollars (the mid currency), not PawCoins — PawCoins is the premium/donate
# currency, and putting routine upkeep behind it is a soft paywall. The price is 10 hours
# of the animal's *healthy* income, converted to USD at the reference rate, so it scales
# with how valuable the patient is.
CURE_INCOME_HOURS = 10
EXPEDITION_SICK_CHANCE = 0.25

# Passive disease outbreaks — pressure that has nothing to do with expeditions. Each time a
# zoo is synced, the time elapsed since the last check gives a chance an outbreak strikes a
# single enclosure and sickens a share of the healthy animals housed there. Striking one
# locality (not the whole zoo) makes crowding many animals into one enclosure a real risk and
# rewards spreading them out. Small zoos are spared so it stays a late-game sink, and vet
# levels lower the chance (reusing development_effect_percent, like the expedition roll).
OUTBREAK_CHANCE_PER_DAY = 0.60
OUTBREAK_SICKEN_FRACTION = 0.30
OUTBREAK_MIN_HEALTHY = 8
# A locality must hold at least this many healthy animals to be a candidate, so an outbreak
# lands somewhere crowded rather than picking off a lone animal in an empty enclosure.
OUTBREAK_MIN_LOCALITY_HEALTHY = 3

# ─── Upkeep ───────────────────────────────────────────────────────────────────
#
# Not in the GDD. Ported from the Telegram bot (`sync_maintenance_cost`), because
# without it rubles have no sink that scales with success and inflate without bound —
# and because GDD §8 assumes weak animals "перестают окупаться" mid-season, which can
# only happen if holding an animal costs something.

# The bot's own coefficient was 2.5 per decade, tuned for a zoo counting animals in the
# billions. Here an animal is an individual and a big zoo is a few hundred, so 2.5 would
# leave upkeep pinned near its 5% floor forever: 5% at one animal, 10% at a hundred.
# At 12 the curve bites where the game actually lives — 17% at ten animals, 29% at a
# hundred, the 45% cap around 1 800.
UPKEEP_BASE_PERCENT = 5.0
UPKEEP_PERCENT_PER_LOG10_ANIMALS = 12.0
UPKEEP_MAX_PERCENT = 45.0

# Infrastructure upgrades turn the five localities into a real development choice.
LOCALITY_UPKEEP_DISCOUNTS: tuple[int, ...] = (0, 1, 3, 6, 9, 12)
# Infrastructure is a long-term investment: the previous ladder was 20x too cheap.
LOCALITY_UPGRADE_COSTS_RUB: tuple[int, ...] = (0, 10_000, 40_000, 160_000, 600_000, 2_000_000)
HABITAT_MATCH_UPKEEP_DISCOUNT = 5


def locality_upkeep_discount(level: int) -> int:
    normalized = int(level or 0)
    return LOCALITY_UPKEEP_DISCOUNTS[min(max(normalized, 0), len(LOCALITY_UPKEEP_DISCOUNTS) - 1)]


def locality_upgrade_cost_rub(level: int) -> int | None:
    if level >= len(LOCALITY_UPGRADE_COSTS_RUB) - 1:
        return None
    return LOCALITY_UPGRADE_COSTS_RUB[level + 1]


# Small, predictable development bonuses shared by veterinary and genetics upgrades.
DEVELOPMENT_EFFECT_PERCENT_BY_LEVEL: tuple[int, ...] = (0, 1, 3, 6, 9, 12)


def development_effect_percent(level: int) -> int:
    normalized = int(level or 0)
    return DEVELOPMENT_EFFECT_PERCENT_BY_LEVEL[min(max(normalized, 0), len(DEVELOPMENT_EFFECT_PERCENT_BY_LEVEL) - 1)]


# Global development tracks. They are capped: every level is useful, but no combination
# can erase the upkeep sink or turn breeding into a guaranteed jackpot.
DEVELOPMENT_MAX_LEVEL = 5
DEVELOPMENT_KINDS: tuple[str, ...] = ("vet", "genetics", "expedition")
DEVELOPMENT_UPGRADE_COSTS_RUB: dict[str, tuple[int, ...]] = {
    "vet": (0, 20_000, 100_000, 400_000, 1_500_000, 5_000_000),
    "genetics": (0, 30_000, 150_000, 600_000, 2_000_000, 7_000_000),
    # The dearest track, because it is the only one that buys raw expedition power and so
    # gates the deepest raids and their legendary-heavy tables.
    "expedition": (0, 50_000, 250_000, 900_000, 3_000_000, 9_000_000),
}


def development_upgrade_cost_rub(kind: str, level: int) -> int | None:
    costs = DEVELOPMENT_UPGRADE_COSTS_RUB[kind]
    if level >= DEVELOPMENT_MAX_LEVEL:
        return None
    return costs[level + 1]


# The expedition corps deliberately does *not* reuse `development_effect_percent`: its 12%
# cap is right for nudging a sickness roll, but a 12% squad bonus could not move a squad
# past a depth the genes alone could not already clear, which is the whole point of the
# track. Genes cap a five-animal squad at 90; this and the forge's `expedition_power` (60%
# each) together take it to 198, just past the strongest possible depth-5 beast (182).
EXPEDITION_CORPS_POWER_PERCENT_BY_LEVEL: tuple[int, ...] = (0, 8, 18, 30, 44, 60)


def expedition_corps_power_percent(level: int) -> int:
    normalized = int(level or 0)
    return EXPEDITION_CORPS_POWER_PERCENT_BY_LEVEL[
        min(max(normalized, 0), len(EXPEDITION_CORPS_POWER_PERCENT_BY_LEVEL) - 1)
    ]

# ─── Diversity ────────────────────────────────────────────────────────────────
#
# Rewards a balanced zoo rather than one whale plus decoration. The effective species
# count is exp(Shannon entropy): an even spread over N species scores N, a monopoly 1.
# The old code multiplied a raw `species_count` and never applied the result at all.

DIVERSITY_BONUS_PERCENT_PER_SPECIES = 1.0

# ─── Breeding ─────────────────────────────────────────────────────────────────
#
# GDD §6 gives five rows: 30 / 45 / 60 / 75 / 90 percent. They are exactly
# 30 + 15 × (tier(a) + tier(b)), which also settles the row the table forgot
# (Неохотно + Активное = 60%).

BREED_BASE_SUCCESS_PCT = 30
BREED_SUCCESS_PCT_PER_TIER = 15
BREED_TIER_INDEX: dict[GeneTier, int] = {"low": 0, "medium": 1, "high": 2}
# GDD §6: "худшее побеждает с вероятностью 60%, лучшее — 40%".
BREED_WORSE_GENE_CHANCE = 0.6


def breed_success_rate(reproduction_a: GeneTier, reproduction_b: GeneTier) -> float:
    tiers = BREED_TIER_INDEX[reproduction_a] + BREED_TIER_INDEX[reproduction_b]
    return (BREED_BASE_SUCCESS_PCT + BREED_SUCCESS_PCT_PER_TIER * tiers) / 100


# Breeding is no longer free: each attempt costs, in rubles, this many hours of the two
# parents' combined *intrinsic* income (genes + rarity, no habitat/sickness/item bonuses).
# It scales with how valuable the animals being bred are — cloning your best pair is the
# priciest breed — gives rubles a sink that grows with the zoo, and is charged on every
# attempt (success is not guaranteed), so genes/genetics that raise success save real money.
BREED_COST_INCOME_HOURS = 4


def breed_cost_rub(parent_income_a: int, parent_income_b: int) -> int:
    """Ruble price of one breeding attempt from the parents' intrinsic per-minute incomes."""
    return round(BREED_COST_INCOME_HOURS * 60 * (parent_income_a + parent_income_b))


# ─── Localities ───────────────────────────────────────────────────────────────
#
# GDD §5: first is free and random, then Базовая цена × 1.5^(кол-во купленных).

MAX_LOCALITIES = 5
# A full five-locality zoo costs 812 500 ₽ after the first free locality. At the
# expected starter net rate this puts the complete infrastructure path around the
# two-week progression milestone; the 1.5× ladder keeps each next purchase legible.
LOCALITY_BASE_PRICE_RUB = 100_000
LOCALITY_PRICE_GROWTH = 1.5

# ─── Packs ────────────────────────────────────────────────────────────────────
#
# GDD §1: one free pack a day, each further pack that day costs more, genes always
# roll 40/40/20. The four "tiers" the client renders are cosmetic labels for the
# first, second, third and fourth-plus pack of the day — they change the price and
# the artwork, never the odds.

PackTier = Literal["rare", "epic", "legendary", "mythic"]
# Tiers climb in this order. Rare is always open; opening a paid tier unlocks the next one
# for the day. Once unlocked, a tier can be reopened any number of times at a fixed price —
# the ladder gates access, it does not lock a tier after one open. Resets daily.
PACK_TIER_ORDER: tuple[PackTier, ...] = ("rare", "epic", "legendary", "mythic")

# The free daily gift rolls a random tier: commonly rare, rarely legendary/mythic. Weights
# are relative (need not sum to 1). Mythic is the top tier, so it is the rarest gift.
DAILY_GIFT_TIER_WEIGHTS: dict[PackTier, float] = {
    "rare": 58.0,
    "epic": 27.0,
    "legendary": 10.0,
    "mythic": 5.0,
}


class PackRewardRange(TypedDict):
    animals: tuple[int, int]
    rub: tuple[int, int]
    usd: tuple[int, int]


# A pack is a bundle, not a single animal; animals remain the main progression reward.
# Paid packs cost dollars (see pack_price_usd), so the dollar reward is tuned to ~25–30%
# of the tier's price: enough that dollars actually drop from packs, but the pack still
# runs a dollar loss, so the bank (rub → usd) stays the real source of dollars. Rouble
# rewards were cut ~3× — the old ranges flooded players with roubles they had no sink for.
PACK_REWARD_RANGES: dict[PackTier, PackRewardRange] = {
    "rare": {"animals": (1, 2), "rub": (180, 500), "usd": (5, 8)},
    "epic": {"animals": (1, 3), "rub": (350, 1_000), "usd": (14, 17)},
    "legendary": {"animals": (2, 5), "rub": (1_300, 3_500), "usd": (28, 34)},
    "mythic": {"animals": (3, 6), "rub": (3_500, 7_000), "usd": (55, 68)},
}

# Price doubles per tier: rare is the cheap entry rung, each tier above costs twice as much.
PACK_TIER_PRICE_MULTIPLIER: dict[PackTier, int] = {"rare": 1, "epic": 2, "legendary": 4, "mythic": 8}
# Each paid opening makes the next paid pack more expensive for that player this season, by a
# flat share of the *base* price (linear, not compounding). Compounding (1.30**n) exploded to
# unreachable numbers for heavy buyers — a whale with 185 paid packs faced a $10^17 rare pack
# and was permanently locked out. Linear growth keeps the price rising all season and always
# reachable: the 4th paid pack costs ~2.4× the first, the 20th ~6×, the 185th ~65×.
PACK_PRICE_GROWTH_PER_PURCHASE = 0.35
# The rare (cheapest paid) pack costs this share of what a pack animal earns over its whole
# life — the main early-game tuning knob.
PACK_PRICE_AS_FRACTION_OF_LIFETIME_INCOME = 0.005
# Packs were 5× too cheap for how much lifetime income each animal prints; this raises the
# entry price of every tier without touching the merchant (which keys off the fraction above).
PACK_BASE_PRICE_MULTIPLIER = 5


def expected_pack_lifetime_income_rub() -> int:
    per_minute = BASE_INCOME_RUB_PER_MIN * expected_gene_income_mult()
    return int(per_minute * expected_lifespan_minutes())


PACK_BASE_PRICE_RUB = int(
    expected_pack_lifetime_income_rub()
    * PACK_PRICE_AS_FRACTION_OF_LIFETIME_INCOME
    * PACK_BASE_PRICE_MULTIPLIER
)


def pack_reward_range(tier: PackTier) -> PackRewardRange:
    return PACK_REWARD_RANGES[tier]


def pack_price_usd_for_tier(
    tier: PackTier,
    discount_mult: float = 1.0,
    purchase_count: int = 0,
) -> int:
    """Return the current dollar price for a tier.

    The tier ladder sets the starting price, then each paid opening made by this player
    this season raises the next price linearly (by 35% of the base per prior opening).
    `discount_mult` is applied last so the forge's pack discount continues to work on the
    dynamic price.
    """
    if purchase_count < 0:
        raise ValueError("purchase_count cannot be negative")
    base_usd = max(1, round(PACK_BASE_PRICE_RUB / RATE_START_RUB_PER_USD))
    raw = base_usd * PACK_TIER_PRICE_MULTIPLIER[tier] * (1 + PACK_PRICE_GROWTH_PER_PURCHASE * purchase_count)
    return max(1, round(raw * discount_mult))


# ─── Expeditions ──────────────────────────────────────────────────────────────
#
# GDD §7. The wild animal's genes come from the habitat's Плохое/Обычное/Хорошее split,
# and on victory that same animal joins the zoo.
#
# The GDD rule is `Сила отряда ≥ сила дикого`. Taken literally it can never fail: the
# weakest legal squad is 3 × 6 = 18 and the strongest possible beast is 18. The beast is
# therefore scaled by `EXPEDITION_WILD_SCALE`, which keeps the GDD's comparison and its
# per-habitat difficulty ladder while making defeat reachable — and makes squad size
# matter, which is what gives weak animals their GDD §9 role as cannon fodder.
#
# That scaling alone still left the feature with a hard, low ceiling. `combat_power` tops
# out at 18 per animal, so a five-animal squad tops out at 90 while the strongest possible
# beast was int(18 × 3.2) = 57: any squad above 57 won every encounter in every habitat,
# 100% of the time. Five plain "medium" animals already score 60. Worse, the beast's genes
# were rolled independently of the squad, so a 90-power squad and a 60-power squad drew the
# identical reward — every point of power above 57 was worth exactly nothing.
#
# Four changes fix that, and they only work together:
#
#   1. `depth` — the player picks how hard the encounter is (`EXPEDITION_DEPTHS`). Depth
#      multiplies the beast's power, so there is no fixed number to out-scale, and it also
#      sets how good the catch is. A habitat caps the depth it can offer, which turns the
#      difficulty ladder into an unlock ladder.
#   2. Graded outcomes (`EXPEDITION_GRADES`) — the win/lose threshold becomes a ratio, so
#      the edges are soft and overshoot keeps paying instead of falling off a cliff.
#   3. Overkill (`expedition_gene_upgrade_chance`) — surplus power upgrades the catch's
#      genes, which is what finally makes a stronger squad win a *better* animal.
#   4. Two power axes that are not genes (the forge's `expedition_power` and the
#      `expedition` development track), because genes alone can never exceed 90.

EXPEDITION_SQUAD_MIN = 3
EXPEDITION_SQUAD_MAX = 5
# Tuned so that three average animals have a real chance in the easy habitats, while
# difficult habitats still reward bringing four or five animals. The old 4.5 multiplier
# made a normal three-animal squad lose almost every encounter, especially in Antarctica.
EXPEDITION_WILD_SCALE = 3.2


class ExpeditionDef(TypedDict):
    minutes: int
    # Плохое / Обычное / Хорошее — the wild animal's gene distribution.
    gene_weights: tuple[float, float, float]
    # Species rarity of the beast this habitat holds. `roll_species_id` used to ignore the
    # habitat entirely, so Antarctica dropped exactly the same species as Fields for four
    # times the wall-clock — the hardest habitat paid the worst per hour and was strictly
    # dominated. Rarity now climbs with the habitat, which is what pays for the longer trip.
    rarity_weights: dict[Rarity, float]
    # The deepest raid this habitat offers. This is the ladder: only Antarctica reaches
    # `Логово`, and `Логово` is the only place the legendary-heavy rarity table appears.
    max_depth: int


EXPEDITIONS: dict[Habitat, ExpeditionDef] = {
    "fields": {
        "minutes": 60,
        "gene_weights": (0.25, 0.45, 0.30),
        "rarity_weights": {"rare": 0.70, "epic": 0.24, "mythic": 0.05, "legendary": 0.01},
        "max_depth": 2,
    },
    "desert": {
        "minutes": 120,
        "gene_weights": (0.20, 0.45, 0.35),
        "rarity_weights": {"rare": 0.55, "epic": 0.31, "mythic": 0.11, "legendary": 0.03},
        "max_depth": 3,
    },
    "forest": {
        "minutes": 150,
        "gene_weights": (0.20, 0.45, 0.35),
        "rarity_weights": {"rare": 0.50, "epic": 0.33, "mythic": 0.14, "legendary": 0.03},
        "max_depth": 3,
    },
    "mountains": {
        "minutes": 180,
        "gene_weights": (0.15, 0.45, 0.40),
        "rarity_weights": {"rare": 0.38, "epic": 0.36, "mythic": 0.20, "legendary": 0.06},
        "max_depth": 4,
    },
    "antarctica": {
        "minutes": 240,
        "gene_weights": (0.10, 0.45, 0.45),
        "rarity_weights": {"rare": 0.25, "epic": 0.35, "mythic": 0.28, "legendary": 0.12},
        "max_depth": 5,
    },
}


class ExpeditionDepthDef(TypedDict):
    name: str
    # Multiplies the beast's already-scaled power. This is the knob that removes the
    # ceiling: there is no squad power that trivialises a depth-5 raid.
    power_scale: float
    # Deeper raids take longer, but nothing like linearly — an 8-hour wait is a wall, not a
    # decision. The habitat's own `minutes` still carries most of the time cost.
    minutes_scale: float
    # How far this depth drags the habitat's gene and rarity tables toward the deep-raid
    # targets below. Depth is what makes a hard fight worth taking.
    quality_shift: float


EXPEDITION_DEPTH_MIN = 1
EXPEDITION_DEPTH_MAX = 5

EXPEDITION_DEPTHS: dict[int, ExpeditionDepthDef] = {
    1: {"name": "Разведка", "power_scale": 1.0, "minutes_scale": 1.00, "quality_shift": 0.00},
    2: {"name": "Вылазка", "power_scale": 1.4, "minutes_scale": 1.15, "quality_shift": 0.15},
    3: {"name": "Рейд", "power_scale": 1.9, "minutes_scale": 1.30, "quality_shift": 0.30},
    4: {"name": "Глубокий рейд", "power_scale": 2.5, "minutes_scale": 1.45, "quality_shift": 0.50},
    5: {"name": "Логово", "power_scale": 3.2, "minutes_scale": 1.60, "quality_shift": 0.70},
}

# What the tables blend *toward* at depth. Depth 1 leaves the habitat untouched, so an
# early player sees exactly the balance that shipped before depth existed.
EXPEDITION_DEPTH_GENE_TARGET: tuple[float, float, float] = (0.0, 0.35, 0.65)
EXPEDITION_DEPTH_RARITY_TARGET: dict[Rarity, float] = {
    "rare": 0.10, "epic": 0.28, "mythic": 0.37, "legendary": 0.25,
}


def _lerp(start: float, end: float, t: float) -> float:
    return start * (1 - t) + end * t


def expedition_max_depth(habitat: Habitat) -> int:
    return EXPEDITIONS[habitat]["max_depth"]


def normalize_expedition_depth(habitat: Habitat, depth: int) -> int:
    """Clamp a requested depth into what this habitat actually offers."""
    return min(max(int(depth), EXPEDITION_DEPTH_MIN), expedition_max_depth(habitat))


def expedition_minutes(habitat: Habitat, depth: int) -> int:
    spec = EXPEDITIONS[habitat]
    return round(spec["minutes"] * EXPEDITION_DEPTHS[depth]["minutes_scale"])


def expedition_gene_weights(habitat: Habitat, depth: int) -> tuple[float, float, float]:
    shift = EXPEDITION_DEPTHS[depth]["quality_shift"]
    base = EXPEDITIONS[habitat]["gene_weights"]
    blended = tuple(_lerp(b, t, shift) for b, t in zip(base, EXPEDITION_DEPTH_GENE_TARGET))
    return cast("tuple[float, float, float]", blended)


def expedition_rarity_weights(habitat: Habitat, depth: int) -> dict[Rarity, float]:
    shift = EXPEDITION_DEPTHS[depth]["quality_shift"]
    base = EXPEDITIONS[habitat]["rarity_weights"]
    return {r: _lerp(base[r], EXPEDITION_DEPTH_RARITY_TARGET[r], shift) for r in RARITIES}


def expedition_wild_scale(depth: int) -> float:
    return EXPEDITION_WILD_SCALE * EXPEDITION_DEPTHS[depth]["power_scale"]


def expedition_wild_power_range(habitat: Habitat, depth: int) -> tuple[int, int, float]:
    """(weakest, strongest, mean) beast this habitat and depth can field.

    Exact rather than sampled — there are only 3³ gene combinations that matter to
    `combat_power`. The client shows this against the squad's own power so the player can
    read the likely grade *before* committing five earners to a raid. Choosing a depth blind
    would be a coin flip, and a coin flip is not the decision this feature is meant to offer.
    """
    weights = expedition_gene_weights(habitat, depth)
    scale = expedition_wild_scale(depth)
    by_tier = dict(zip(GENE_TIERS, weights))
    lowest = int(combat_power("low", "low", "low") * scale)
    highest = int(combat_power("high", "high", "high") * scale)
    mean = 0.0
    for survival in GENE_TIERS:
        for appearance in GENE_TIERS:
            for size in GENE_TIERS:
                probability = by_tier[survival] * by_tier[appearance] * by_tier[size]
                mean += probability * int(combat_power(survival, appearance, size) * scale)
    return max(1, lowest), max(1, highest), mean


# ─── Expedition outcome grades ────────────────────────────────────────────────
#
# `squad_power >= wild_power` is a cliff: one point below it you lose an animal, one point
# above it you take no damage at all, and a thousand points above it changes nothing. The
# comparison is now a ratio, and the ratio picks a row here. Rows are ordered by
# `min_ratio` ascending; `expedition_grade` walks them and takes the last one that fits.
#
# `outcome` in the database stays "victory"/"defeat" (see `ck_expeditions_outcome`); the
# grade is the finer story told in `result_json`.


class ExpeditionGradeDef(TypedDict):
    key: str
    label: str
    min_ratio: float
    captured: bool
    # Only an outright rout still kills. A narrow loss costs the squad its health, not a life.
    casualty: bool
    # Scales `EXPEDITION_SICK_CHANCE` for the survivors: a bloodbath wounds, a clean win never does.
    sick_multiplier: float
    # Multiplies the currency trophy. Every capture pays one — gating the trophy on overkill
    # alone would mean a depth-5 raid (which the best possible build wins at a ratio of only
    # ~1.26) paid nothing while a trivial depth-1 farm always did, inverting the incentive
    # the depth ladder exists to create.
    loot_multiplier: float
    # Dollars are the bank's job; only an outright dominant win mints any (see `expedition_loot`).
    pays_usd: bool


EXPEDITION_GRADES: tuple[ExpeditionGradeDef, ...] = (
    {
        "key": "rout", "label": "Разгром", "min_ratio": 0.0,
        "captured": False, "casualty": True, "sick_multiplier": 2.0,
        "loot_multiplier": 0.0, "pays_usd": False,
    },
    {
        "key": "defeat", "label": "Отступление", "min_ratio": 0.75,
        "captured": False, "casualty": False, "sick_multiplier": 1.0,
        "loot_multiplier": 0.0, "pays_usd": False,
    },
    {
        "key": "pyrrhic", "label": "Тяжёлая победа", "min_ratio": 0.95,
        "captured": True, "casualty": False, "sick_multiplier": 1.5,
        "loot_multiplier": 1.0, "pays_usd": False,
    },
    {
        "key": "victory", "label": "Победа", "min_ratio": 1.15,
        "captured": True, "casualty": False, "sick_multiplier": 0.0,
        "loot_multiplier": 1.0, "pays_usd": False,
    },
    {
        "key": "confident", "label": "Уверенная победа", "min_ratio": 1.6,
        "captured": True, "casualty": False, "sick_multiplier": 0.0,
        "loot_multiplier": 1.5, "pays_usd": False,
    },
    {
        "key": "dominant", "label": "Доминация", "min_ratio": 2.2,
        "captured": True, "casualty": False, "sick_multiplier": 0.0,
        "loot_multiplier": 2.0, "pays_usd": True,
    },
)

EXPEDITION_GRADE_KEYS: tuple[str, ...] = tuple(g["key"] for g in EXPEDITION_GRADES)


def expedition_grade(ratio: float) -> ExpeditionGradeDef:
    """The row `squad_power / wild_power` lands in. Never returns None: `rout` starts at 0."""
    match = EXPEDITION_GRADES[0]
    for grade in EXPEDITION_GRADES:
        if ratio >= grade["min_ratio"]:
            match = grade
    return match


# Surplus power upgrades the catch's genes — the single change that makes squad power worth
# investing in past the win threshold. Ramps from `START` and saturates at `MAX`, so a
# stronger squad always catches a better animal without ever guaranteeing an all-high one.
EXPEDITION_OVERKILL_UPGRADE_START = 1.2
EXPEDITION_OVERKILL_UPGRADE_SLOPE = 0.35
EXPEDITION_OVERKILL_UPGRADE_MAX = 0.5
# Only at `dominant`: crushing a raid far below your weight occasionally yields a second beast.
EXPEDITION_DOMINANT_SECOND_CATCH_CHANCE = 0.35


def expedition_gene_upgrade_chance(ratio: float) -> float:
    """Per-gene chance that the catch's gene is bumped one tier, from how hard you won."""
    raw = (ratio - EXPEDITION_OVERKILL_UPGRADE_START) * EXPEDITION_OVERKILL_UPGRADE_SLOPE
    return min(max(raw, 0.0), EXPEDITION_OVERKILL_UPGRADE_MAX)


# The currency trophy. It scales with the beast's power *and* the hours the squad was away,
# so a six-hour depth-5 raid pays for the trip while an hourly depth-1 farm stays a trickle.
#
# The catch is the reward; this is a garnish on it, and the coefficient is chosen to keep it
# one: across every habitat and depth the trophy runs 1–10% of what the captured animal will
# itself earn over its life (up to ~19% on a dominant win). That is the bound
# `test_the_trophy_never_outgrows_the_catch` holds it to.
#
# It is deliberately *not* bounded by the income the squad forgoes while away. A deep raid
# does out-earn what five median animals would have made at home — that is the point of
# risking them — and pretending otherwise would mean pricing the trophy into irrelevance.
# The faucet is safe because it is gated: reaching the depths that pay well costs a 13M ₽
# corps plus forge items, and at that stage the trophy is a few percent of the zoo's hourly
# income, while `upkeep_rub_per_min` still scales with every animal the raid brings home.
EXPEDITION_LOOT_RUB_PER_POWER_HOUR = 250
# Dollars only at `dominant`, thin, and deliberately not scaled by duration: the bank
# (rub → usd) stays the real dollar source, exactly as with packs.
EXPEDITION_LOOT_USD_PER_POWER = 0.25


def expedition_loot(wild_power: int, minutes: int, grade: ExpeditionGradeDef) -> tuple[int, int]:
    """(rubles, dollars) won from a beast of `wild_power` after a `minutes`-long raid."""
    if grade["loot_multiplier"] <= 0:
        return 0, 0
    hours = minutes / 60
    rub = int(wild_power * EXPEDITION_LOOT_RUB_PER_POWER_HOUR * hours * grade["loot_multiplier"])
    usd = int(wild_power * EXPEDITION_LOOT_USD_PER_POWER) if grade["pays_usd"] else 0
    return rub, usd

# ─── Merchant ─────────────────────────────────────────────────────────────────
#
# Not in the GDD. An offer is one concrete animal with visible genes, so it is priced
# from what that animal will earn over its own lifetime. The merchant is a guaranteed
# purchase, so it costs twice the blind pack fraction, while still leaving a clear
# payback window for the player.

MERCHANT_SLOTS = 3
MERCHANT_REFRESH_HOURS = 24
MERCHANT_DISCOUNTS = (5, 10, 15, 20, 25, 30)
# Twice the pack's 0.5% fraction: the merchant shows the genes, the pack does not.
MERCHANT_PRICE_AS_FRACTION_OF_LIFETIME_INCOME = PACK_PRICE_AS_FRACTION_OF_LIFETIME_INCOME * 2


def merchant_price_rub(
    survival: GeneTier,
    appearance: GeneTier,
    size: GeneTier,
    species_rarity: Rarity,
) -> int:
    lifetime = lifetime_income_rub(survival, appearance, size)
    return int(lifetime * SPECIES_RARITY_INCOME_MULT[species_rarity] * MERCHANT_PRICE_AS_FRACTION_OF_LIFETIME_INCOME)


# ─── Bank ─────────────────────────────────────────────────────────────────────
#
# One-way funnel, exactly as in the Telegram bot: rubles come from animals, dollars buy
# upgrades, and there is no usd → rub direction. That is what makes a swinging rate safe
# to publish. The old web bank quoted both directions around a ±15% oscillation with a
# 2% spread, so waiting for a cheap minute to buy and a dear one to sell printed 26% a
# cycle, risk-free.
#
# The rate is a random walk persisted in `bank_rates`, not a pure function of the clock.

RATE_START_RUB_PER_USD = 90
RATE_MIN_RUB_PER_USD = 60
RATE_MAX_RUB_PER_USD = 130
RATE_PERIOD_SECONDS = 60
RATE_STEPS = (1, 2, 3, 4, 5)
BANK_FEE_PERCENT = 3
# The referrer's cut of every dollar their referral buys.
REFERRAL_PERCENT = 5

# ─── Forge ────────────────────────────────────────────────────────────────────

ItemRarity = Literal["common", "rare", "epic", "mythical", "legendary"]
ITEM_RARITIES: tuple[ItemRarity, ...] = ("common", "rare", "epic", "mythical", "legendary")
# `legendary` never drops; it is only reachable by merging.
ITEM_RARITY_DROP_WEIGHTS = (0.50, 0.30, 0.13, 0.07)
ITEM_PROPERTY_COUNT: dict[ItemRarity, int] = {
    "common": 1, "rare": 2, "epic": 3, "mythical": 4, "legendary": 5,
}
ITEM_RARITY_BY_PROPERTY_COUNT: dict[int, ItemRarity] = {
    1: "common", 2: "rare", 3: "epic", 4: "mythical", 5: "legendary",
}
ITEM_RARITY_ICON: dict[ItemRarity, str] = {
    "common": "🔩", "rare": "💙", "epic": "💜", "mythical": "🔴", "legendary": "⭐",
}
ITEM_RARITY_NAME: dict[ItemRarity, str] = {
    "common": "Обычный", "rare": "Редкий", "epic": "Эпический",
    "mythical": "Мифический", "legendary": "Легендарный",
}

FORGE_CREATE_BASE_USD = 80_000
FORGE_CREATE_PAW = 350
# Each item the player has created (since the epoch below) makes the next one 20% of the base
# more expensive — linear, not compounding. Compounding (1.15**n) re-explodes for heavy
# forgers: at ~16 creations/day a whale hit an unreachable price within days, the same wall
# the anchor was meant to avoid. Linear keeps the price rising monotonically while staying
# reachable. The counter is the number of `forge_create` ledger entries (see
# `forge.forge_create`), so it only ever rises — selling or merging an item away never
# cheapens the next creation.
FORGE_CREATE_GROWTH = 0.20
FORGE_UPGRADE_BASE_USD = 5_000
FORGE_UPGRADE_FAIL_PCT_PER_LEVEL = 8
# Merging two items into one is a flat, deliberately steep dollar fee — set well above any
# item's resale, so merge-then-sell can never turn a profit regardless of the inputs.
FORGE_MERGE_COST_USD = 100_000
FORGE_MAX_ITEM_LEVEL = 12
FORGE_MAX_ACTIVE_ITEMS = 3


# Escalation is counted only from this instant, not from the beginning of time. When this
# pricing shipped, forging had been near-free (base $120) and some players had already forged
# thousands of items — 1.15^2000 is effectively infinite, which would lock forging forever.
# So we anchor the counter here: only `forge_create` ledger rows created at or after this
# moment escalate the price. Everyone restarts at the base; selling still never cheapens it.
FORGE_CREATE_COUNTER_EPOCH = datetime(2026, 7, 14, 23, 45, 0, tzinfo=timezone.utc)


def forge_create_cost_usd(creations: int) -> int:
    """Dollar price to forge the *next* item, given how many the player has created since
    `FORGE_CREATE_COUNTER_EPOCH`. Escalates linearly by 20% of the base per prior creation,
    growing monotonically."""
    return int(FORGE_CREATE_BASE_USD * (1 + FORGE_CREATE_GROWTH * max(0, creations)))


# Selling is a partial refund — never a profit. Resale returns 40% of the create price plus
# 40% of each upgrade level's base. It stays safe because the create price is an $80k+ sink
# and merging is a flat $100k fee: both dwarf the 40% resale, so no create/merge→sell loop
# turns a profit. Resale is rarity-independent (you pay the same to create any rarity), so
# only the level (upgrade investment) raises the price.
FORGE_SELL_REFUND_RATE = 0.4
FORGE_SELL_PER_LEVEL_USD = int(FORGE_UPGRADE_BASE_USD * FORGE_SELL_REFUND_RATE)


def item_sell_price_usd(rarity: ItemRarity, level: int) -> int:
    del rarity  # resale is rarity-independent — see note above
    base = round(FORGE_CREATE_BASE_USD * FORGE_SELL_REFUND_RATE)
    return base + max(0, level) * FORGE_SELL_PER_LEVEL_USD


# ─── Item properties ──────────────────────────────────────────────────────────
#
# Every property names the function that reads it. A property with no consumer is a lie
# told to a player who paid Telegram Stars for it, so the set is closed: adding a row
# here without wiring it up fails `test_every_item_property_is_applied`.
#
# Only *active* items count, at most `FORGE_MAX_ACTIVE_ITEMS` of them, and values of the
# same kind sum before being clipped to `cap` — the same rule as the Telegram bot's
# `synchronize_info_about_items`.

PropertyKind = Literal[
    "income_total",
    "income_species",
    "discount_upkeep",
    "discount_packs",
    "discount_locality",
    "discount_bank",
    "duel_moves",
    "duel_bonus",
    "bonus_rerolls",
    "expedition_power",
]


class PropertyDef(TypedDict):
    label: str
    unit: Literal["percent_bonus", "percent_discount", "flat"]
    per_species: bool
    cap: int | None
    weight: int
    ranges: dict[ItemRarity, tuple[int, int]]
    applies_to: str


ITEM_PROPERTIES: dict[PropertyKind, PropertyDef] = {
    "income_total": {
        "label": "Общий доход",
        "unit": "percent_bonus",
        "per_species": False,
        "cap": None,
        "weight": 25,
        "ranges": {
            "common": (5, 7), "rare": (10, 20), "epic": (25, 30),
            "mythical": (30, 45), "legendary": (30, 45),
        },
        "applies_to": "income.calc_player_income",
    },
    "income_species": {
        "label": "Доход вида",
        "unit": "percent_bonus",
        "per_species": True,
        "cap": None,
        "weight": 25,
        "ranges": {
            "common": (1, 5), "rare": (3, 9), "epic": (9, 14),
            "mythical": (10, 20), "legendary": (10, 20),
        },
        "applies_to": "income.animal_income",
    },
    "discount_upkeep": {
        "label": "Снижение содержания",
        "unit": "percent_discount",
        "per_species": False,
        "cap": 50,
        "weight": 18,
        "ranges": {
            "common": (3, 6), "rare": (8, 12), "epic": (15, 20),
            "mythical": (25, 35), "legendary": (35, 45),
        },
        "applies_to": "income.upkeep_rub_per_min",
    },
    "discount_packs": {
        "label": "Скидка на паки",
        "unit": "percent_discount",
        "per_species": False,
        "cap": 80,
        "weight": 15,
        "ranges": {
            "common": (3, 10), "rare": (10, 14), "epic": (20, 25),
            "mythical": (30, 50), "legendary": (30, 50),
        },
        "applies_to": "progression.open_pack",
    },
    "discount_locality": {
        "label": "Скидка на местности",
        "unit": "percent_discount",
        "per_species": False,
        "cap": 80,
        "weight": 15,
        "ranges": {
            "common": (5, 9), "rare": (9, 12), "epic": (10, 20),
            "mythical": (15, 20), "legendary": (15, 20),
        },
        "applies_to": "progression.locality_price_rub",
    },
    "discount_bank": {
        "label": "Скидка на курс банка",
        "unit": "percent_discount",
        "per_species": False,
        "cap": 80,
        "weight": 20,
        "ranges": {
            "common": (5, 10), "rare": (10, 20), "epic": (20, 25),
            "mythical": (23, 30), "legendary": (23, 30),
        },
        "applies_to": "economy.effective_rate",
    },
    "duel_moves": {
        "label": "Доп. броски в дуэли",
        "unit": "flat",
        "per_species": False,
        "cap": None,
        "weight": 10,
        "ranges": {
            "common": (1, 1), "rare": (1, 2), "epic": (1, 3),
            "mythical": (1, 4), "legendary": (1, 5),
        },
        "applies_to": "games.join_duel",
    },
    "duel_bonus": {
        "label": "Бонус к счёту в дуэли",
        "unit": "flat",
        "per_species": False,
        "cap": None,
        "weight": 10,
        "ranges": {
            "common": (1, 2), "rare": (2, 4), "epic": (3, 6),
            "mythical": (4, 8), "legendary": (5, 10),
        },
        "applies_to": "games.join_duel",
    },
    "bonus_rerolls": {
        "label": "Перебросы бонуса",
        "unit": "flat",
        "per_species": False,
        "cap": None,
        "weight": 10,
        "ranges": {
            "common": (1, 1), "rare": (1, 2), "epic": (1, 3),
            "mythical": (1, 4), "legendary": (1, 5),
        },
        "applies_to": "status.reroll_daily_bonus",
    },
    # The forge's half of the non-gene power axis. Capped at 60% so that even a perfect
    # three-item loadout plus a maxed corps lands a full-gene squad at 198 — enough to
    # clear a depth-5 raid reliably, never enough to dominate one.
    "expedition_power": {
        "label": "Сила в экспедиции",
        "unit": "percent_bonus",
        "per_species": False,
        "cap": 60,
        "weight": 15,
        "ranges": {
            "common": (4, 8), "rare": (8, 14), "epic": (14, 22),
            "mythical": (20, 30), "legendary": (25, 40),
        },
        "applies_to": "progression.squad_power",
    },
}

PROPERTY_KINDS: tuple[PropertyKind, ...] = tuple(ITEM_PROPERTIES)

# ─── Duels and solo games ─────────────────────────────────────────────────────
#
# `duel_moves` and `duel_bonus` apply only to player-versus-player duels, where the pot
# is zero-sum. They deliberately never touch solo games: the 4% house edge there is the
# only thing draining rubles out of the casino, and a 10% bet refund would invert it.

GAME_KINDS = ("basketball", "darts", "bowling", "dice", "football")
MAX_STAKE_RUB = 10_000_000_000
SOLO_STAKE_PCTS = (5, 10, 15)
DUEL_BASE_MOVES = 5
DUEL_MAX_PLAYERS = 3
DUEL_DURATION_MINUTES = 10
DUEL_REWARD_DISTRIBUTION = (70, 20, 10)
DUEL_DICE_SIDES = 6

SOLO_MATCH_MIN_ROUNDS = 2
SOLO_MATCH_MAX_ROUNDS = 7
SOLO_WIN_CHANCE_PCT = 48

# ─── Cocktail ─────────────────────────────────────────────────────────────────

# Must stay in sync with the fruit palette rendered by the client (CocktailTab.tsx):
# the secret is drawn from this set, so any mismatch makes the puzzle unsolvable and
# rejects fruits the player is allowed to pick.
COCKTAIL_FRUITS = ("🍓", "🫐", "🍏", "🍐", "🍇", "🍒")
COCKTAIL_LENGTH = 4
COCKTAIL_BASE_ATTEMPTS = 10
COCKTAIL_REWARD_PAW = 150

# ─── Daily bonus ──────────────────────────────────────────────────────────────

BONUS_KINDS: tuple[str, ...] = ("rub", "usd", "paw", "locality", "animal")
# 46% rubles, 23% dollars, 23% PawCoins, 4% locality, 4% animal.
BONUS_KIND_WEIGHTS: dict[str, int] = {
    "rub": 46,
    "usd": 23,
    "paw": 23,
    "locality": 4,
    "animal": 4,
}
# The old bot used a weighted jackpot table rather than a uniform range. The top
# rewards are intentionally rare: they add excitement without turning a daily claim
# into a reliable source of dollars or millions of rubles.
BONUS_REWARD_VALUES: dict[Currency, tuple[int, ...]] = {
    "rub": (100, 1_000, 5_000, 1_000_000),
    "usd": (5, 50, 200, 1_000, 1_000_000),
    "paw": tuple(range(10, 51)),
}
BONUS_REWARD_WEIGHTS: dict[Currency, tuple[int, ...]] = {
    # 94% / 5% / 0.99% / 0.01%
    "rub": (9_400, 500, 99, 1),
    # 97% / 2.5% / 0.45% / 0.04% / 0.01%
    "usd": (9_700, 250, 45, 4, 1),
    # Uniform 10–50 PawCoins.
    "paw": (1,) * 41,
}

# ─── Season, clans, transfers, donations ──────────────────────────────────────

SEASON_LENGTH_DAYS = 30  # GDD §8
CLAN_MAX_MEMBERS = 50
CLAN_CREATE_COST_USD = 1
TRANSFER_MAX_CLAIMS = 100
TRANSFER_TTL_HOURS = 72
TOP_LIMIT = 20
STARS_TO_PAW = 10
# A referral should feel like a meaningful milestone, while still being paid only once
# for a genuinely new player. It is intentionally close to the price of an epic pack.
REFERRAL_SIGNUP_REWARD_USD = 50
# A new player who joins through a valid referral link starts with a larger balance.
REFERRAL_NEW_PLAYER_REWARD_USD = 25


# ─── Animal names ─────────────────────────────────────────────────────────────
#
# Every animal gets an individual name so duplicates of the same species are easy to
# tell apart. Renaissance-era figures — artists, scientists, writers, explorers — give a
# large, distinctive pool that rarely repeats.
ANIMAL_NAME_POOL: tuple[str, ...] = (
    "Леонардо", "Микеланджело", "Рафаэль", "Донателло", "Боттичелли", "Тициан",
    "Караваджо", "Джотто", "Дюрер", "Босх", "Веласкес", "Тинторетто", "Веронезе",
    "Джорджоне", "Беллини", "Мантенья", "Верроккьо", "Перуджино", "Гольбейн", "Кранах",
    "Брунеллески", "Гиберти", "Браманте", "Челлини", "Палладио",
    "Галилей", "Коперник", "Кеплер", "Везалий", "Бруно", "Парацельс", "Кардано",
    "Данте", "Петрарка", "Боккаччо", "Макиавелли", "Эразм", "Монтень", "Рабле",
    "Шекспир", "Сервантес", "Колумб", "Магеллан", "Веспуччи", "Дрейк",
    "Медичи", "Лоренцо", "Козимо", "Гутенберг", "Америго", "Никколо", "Сандро",
    "Джулиано", "Пико",
)
