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

from typing import Literal, TypedDict

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
LOCALITY_UPGRADE_COSTS_RUB: tuple[int, ...] = (0, 500, 2_000, 8_000, 30_000, 100_000)
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
DEVELOPMENT_UPGRADE_COSTS_RUB: dict[str, tuple[int, ...]] = {
    "vet": (0, 1_000, 5_000, 20_000, 75_000, 250_000),
    "genetics": (0, 1_500, 7_500, 30_000, 100_000, 350_000),
}


def development_upgrade_cost_rub(kind: str, level: int) -> int | None:
    costs = DEVELOPMENT_UPGRADE_COSTS_RUB[kind]
    if level >= DEVELOPMENT_MAX_LEVEL:
        return None
    return costs[level + 1]

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


# ─── Localities ───────────────────────────────────────────────────────────────
#
# GDD §5: first is free and random, then Базовая цена × 1.5^(кол-во купленных).

MAX_LOCALITIES = 5
LOCALITY_BASE_PRICE_RUB = 500
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
# The rare (cheapest paid) pack costs this share of what a pack animal earns over its whole
# life — the main early-game tuning knob.
PACK_PRICE_AS_FRACTION_OF_LIFETIME_INCOME = 0.005


def expected_pack_lifetime_income_rub() -> int:
    per_minute = BASE_INCOME_RUB_PER_MIN * expected_gene_income_mult()
    return int(per_minute * expected_lifespan_minutes())


PACK_BASE_PRICE_RUB = int(expected_pack_lifetime_income_rub() * PACK_PRICE_AS_FRACTION_OF_LIFETIME_INCOME)


def pack_reward_range(tier: PackTier) -> PackRewardRange:
    return PACK_REWARD_RANGES[tier]


def pack_price_usd_for_tier(tier: PackTier, discount_mult: float = 1.0) -> int:
    """Fixed dollar price of a tier (rare base, ×2 per tier up). Paying in dollars is what
    gives the bank (rub → usd) a purpose. `discount_mult` (<1) applies the player's
    `discount_packs` item bonus."""
    base_usd = max(1, round(PACK_BASE_PRICE_RUB / RATE_START_RUB_PER_USD))
    raw = base_usd * PACK_TIER_PRICE_MULTIPLIER[tier]
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


EXPEDITIONS: dict[Habitat, ExpeditionDef] = {
    "fields": {"minutes": 60, "gene_weights": (0.25, 0.45, 0.30)},
    "desert": {"minutes": 120, "gene_weights": (0.20, 0.45, 0.35)},
    "forest": {"minutes": 150, "gene_weights": (0.20, 0.45, 0.35)},
    "mountains": {"minutes": 180, "gene_weights": (0.15, 0.45, 0.40)},
    "antarctica": {"minutes": 240, "gene_weights": (0.10, 0.45, 0.45)},
}

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

FORGE_CREATE_BASE_USD = 120
FORGE_CREATE_PAW = 350
FORGE_CREATE_GROWTH = 1.15
FORGE_UPGRADE_BASE_USD = 300
FORGE_UPGRADE_FAIL_PCT_PER_LEVEL = 8
FORGE_MERGE_BASE_USD = 1_000
FORGE_MAX_ITEM_LEVEL = 12
FORGE_MAX_ACTIVE_ITEMS = 3

# Selling is a partial refund of what an item costs to make — never a profit. A freshly
# created item always sells for less than the create price, which kills the create→sell
# arbitrage (you can't roll a lucky rarity and dump it for gain). Rarity drives an item's
# *bonuses*, not its resale: you pay the same to create any rarity, so resale is flat and
# only the level (upgrade investment) raises it.
FORGE_SELL_REFUND_RATE = 0.4
FORGE_SELL_PER_LEVEL_USD = int(FORGE_UPGRADE_BASE_USD * 0.4)


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
}

PROPERTY_KINDS: tuple[PropertyKind, ...] = tuple(ITEM_PROPERTIES)

# ─── Duels and solo games ─────────────────────────────────────────────────────
#
# `duel_moves` and `duel_bonus` apply only to player-versus-player duels, where the pot
# is zero-sum. They deliberately never touch solo games: the 4% house edge there is the
# only thing draining rubles out of the casino, and a 10% bet refund would invert it.

GAME_KINDS = ("basketball", "darts", "bowling", "dice", "football")
MAX_STAKE_RUB = 10_000_000_000
DUEL_BASE_MOVES = 5
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

BONUS_KINDS: tuple[Currency, ...] = ("rub", "rub", "usd", "paw")
BONUS_RANGES: dict[Currency, tuple[int, int]] = {
    "rub": (1, 100),
    "usd": (1, 10),
    "paw": (1, 5),
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
