"""Income, upkeep and the passive accrual of rubles.

GDD §3:  Доход = База вида × М_выживаемость × М_внешность × М_размер × М_местность
GDD §7:  animals away on an expedition earn nothing.

On top of that the zoo applies, in order: the sickness penalty (halves one animal), the
per-species item bonus, the global item bonus, and the diversity bonus. Upkeep — a share
of income that grows with the size of the zoo — is the only ruble sink that scales.

Nothing here compares against SQL `NOW()`: the database server's clock may not be UTC,
while every stored timestamp is. Times are always bound from Python.
"""

from __future__ import annotations

import math
from datetime import datetime
from math import trunc

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from api.app.db.models import Animal, Clan, ClanMember, Expedition, ExpeditionMember, Locality, Player, utcnow
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import ledger
from api.app.zoopark.bonuses import Bonuses
from api.app.zoopark.catalog import (
    BASE_INCOME_RUB_PER_MIN,
    CURE_INCOME_HOURS,
    DIVERSITY_BONUS_PERCENT_PER_SPECIES,
    HABITAT_MATCH_BONUS,
    HABITAT_MATCH_UPKEEP_DISCOUNT,
    RATE_START_RUB_PER_USD,
    SICK_INCOME_MULT,
    SPECIES_BY_ID,
    SPECIES_RARITY_INCOME_MULT,
    development_effect_percent,
    locality_upkeep_discount,
    UPKEEP_BASE_PERCENT,
    UPKEEP_MAX_PERCENT,
    UPKEEP_PERCENT_PER_LOG10_ANIMALS,
    GeneTier,
    Rarity,
    gene_income_mult,
)
from api.app.zoopark.notifications import enqueue_animal_death


def alive_clause(now: datetime | None = None):
    """An animal is alive iff it has not been removed and its clock has not run out.

    There is no `is_alive` column to fall out of date, and therefore no sweeper job whose
    absence makes `/api/me` show dead animals earning money.
    """
    moment = now or utcnow()
    return and_(Animal.removed_at.is_(None), Animal.dies_at > moment)


def on_expedition_subquery():
    return (
        select(ExpeditionMember.animal_id)
        .join(Expedition, Expedition.id == ExpeditionMember.expedition_id)
        .where(Expedition.resolved_at.is_(None))
        .scalar_subquery()
    )


def animal_income_rub_per_min(
    *,
    survival: GeneTier,
    appearance: GeneTier,
    size: GeneTier,
    habitat_matches: bool,
    is_sick: bool = False,
    species_multiplier: float = 1.0,
    species_rarity: Rarity | None = None,
) -> int:
    value = BASE_INCOME_RUB_PER_MIN * gene_income_mult(survival, appearance, size)
    if species_rarity is not None:
        value *= SPECIES_RARITY_INCOME_MULT[species_rarity]
    if habitat_matches:
        value *= HABITAT_MATCH_BONUS
    if is_sick:
        value *= SICK_INCOME_MULT
    value *= species_multiplier
    return int(value)


def animal_income(animal: Animal, locality_habitat: str | None, bonuses: Bonuses) -> int:
    return animal_income_rub_per_min(
        survival=animal.gene_survival,  # type: ignore[arg-type]
        appearance=animal.gene_appearance,  # type: ignore[arg-type]
        size=animal.gene_size,  # type: ignore[arg-type]
        habitat_matches=bool(locality_habitat) and locality_habitat == animal.habitat,
        is_sick=animal.sick_since is not None,
        species_multiplier=bonuses.species_income_multiplier(animal.species_id),
        species_rarity=SPECIES_BY_ID[animal.species_id]["rarity"],
    )


def cure_cost_usd(animal: Animal, locality_habitat: str | None, bonuses: Bonuses, vet_level: int = 0) -> int:
    """Price of curing this animal, in dollars: CURE_INCOME_HOURS of its *healthy* income
    (the sick penalty is excluded so the cost reflects the animal's real worth), converted
    to USD at the reference rate. Authoritative — recompute this on cure, never trust the
    client's number."""
    healthy_rub_per_min = animal_income_rub_per_min(
        survival=animal.gene_survival,  # type: ignore[arg-type]
        appearance=animal.gene_appearance,  # type: ignore[arg-type]
        size=animal.gene_size,  # type: ignore[arg-type]
        habitat_matches=bool(locality_habitat) and locality_habitat == animal.habitat,
        is_sick=False,
        species_multiplier=bonuses.species_income_multiplier(animal.species_id),
        species_rarity=SPECIES_BY_ID[animal.species_id]["rarity"],
    )
    cost_rub = healthy_rub_per_min * 60 * CURE_INCOME_HOURS
    clinic_discount = development_effect_percent(vet_level)
    return max(1, round(cost_rub / RATE_START_RUB_PER_USD * (100 - clinic_discount) / 100))


def effective_species_count(species_counts: list[int]) -> float:
    """exp(Shannon entropy): an even spread over N species scores N, a monopoly scores 1.

    A raw `len(species)` pays the same for "ten of each" and "ninety-one of one plus nine
    singletons", which is why the old `diversity_bonus_per_species * species_count` was
    not only never applied to income but also the wrong shape.
    """
    total = sum(species_counts)
    if total <= 0:
        return 0.0
    entropy = -sum((count / total) * math.log(count / total) for count in species_counts if count > 0)
    return math.exp(entropy)


def diversity_multiplier(species_counts: list[int]) -> float:
    """1 + `DIVERSITY_BONUS_PERCENT_PER_SPECIES`% per effective species."""
    return 1 + effective_species_count(species_counts) * DIVERSITY_BONUS_PERCENT_PER_SPECIES / 100


def upkeep_rub_per_min(income_rub_per_min: int, animal_count: int) -> int:
    """A percentage of income that grows logarithmically with the size of the zoo."""
    if animal_count <= 0 or income_rub_per_min <= 0:
        return 0
    percent = UPKEEP_BASE_PERCENT + UPKEEP_PERCENT_PER_LOG10_ANIMALS * math.log10(animal_count)
    percent = min(percent, UPKEEP_MAX_PERCENT)
    return int(income_rub_per_min * percent / 100)


def calc_player_income(
    session: Session,
    player_id: int,
    bonuses: Bonuses | None = None,
    *,
    now: datetime | None = None,
) -> tuple[int, int]:
    """(income per minute, upkeep per minute) for everything the player currently owns."""
    active_bonuses = bonuses if bonuses is not None else bonuses_module.load(session, player_id)
    moment = now or utcnow()

    rows = session.execute(
        select(Animal, Locality.habitat, Locality.level)
        .outerjoin(Locality, Animal.locality_id == Locality.id)
        .where(
            Animal.player_id == player_id,
            alive_clause(moment),
            Animal.id.not_in(on_expedition_subquery()),
        )
    ).all()

    clan_specialization = session.scalar(
        select(Clan.specialization)
        .join(ClanMember, ClanMember.clan_id == Clan.id)
        .where(ClanMember.player_id == player_id)
    )

    total = 0
    locality_discounted_income = 0.0
    level_discounted_income = 0.0
    levelled_locality_levels = 0
    counts_by_species: dict[int, int] = {}
    for animal, locality_habitat, locality_level in rows:
        current_income = animal_income(animal, locality_habitat, active_bonuses)
        if clan_specialization == "specialist":
            rarity = SPECIES_BY_ID[animal.species_id]["rarity"]
            if rarity in ("epic", "mythic", "legendary"):
                current_income = round(current_income * 1.5)
            elif rarity == "rare":
                current_income = round(current_income * 0.8)
        total += current_income
        upkeep_discount = locality_upkeep_discount(locality_level)
        level_discounted_income += current_income * upkeep_discount / 100
        levelled_locality_levels += max(int(locality_level or 0), 0)
        if locality_habitat and locality_habitat == animal.habitat:
            upkeep_discount += HABITAT_MATCH_UPKEEP_DISCOUNT
        locality_discounted_income += current_income * upkeep_discount / 100
        counts_by_species[animal.species_id] = counts_by_species.get(animal.species_id, 0) + 1

    # After the 100× denomination rebase, truncating every multiplier is too coarse for
    # small zoos (e.g. 42 × 1.30 should become 55, not 54). Round each derived rate so
    # percentage bonuses remain visible at the new scale.
    total = round(total * active_bonuses.income_multiplier() * diversity_multiplier(list(counts_by_species.values())))
    if clan_specialization == "megapark":
        total = round(total * (1 + min(60, len(rows) // 10) / 100))
    elif clan_specialization == "wild":
        total = round(total * (1 + len(counts_by_species) * 3 / 100))

    base_upkeep = upkeep_rub_per_min(total, len(rows))
    base_percent = 0.0 if total <= 0 else base_upkeep / total
    locality_relief = round(locality_discounted_income * base_percent)
    if levelled_locality_levels > 0 and base_upkeep > 0:
        # A levelled locality should be visible even in a very small zoo where one
        # percentage point would otherwise disappear into integer rounding. The extra
        # minimum is based on upgrade levels, so a habitat-match bonus cannot consume
        # the entire visible effect of the first locality upgrade.
        non_level_discounted_income = max(locality_discounted_income - level_discounted_income, 0)
        locality_relief = max(
            round(non_level_discounted_income * base_percent)
            + round(level_discounted_income * base_percent)
            + levelled_locality_levels
            + 1,
            locality_relief,
        )
    elif locality_discounted_income > 0 and base_upkeep > 0:
        locality_relief = max(1, locality_relief)
    upkeep = max(0, base_upkeep - locality_relief)
    if clan_specialization == "megapark":
        upkeep = round(upkeep * 1.15)
    upkeep = max(0, round(upkeep * active_bonuses.upkeep_discount_multiplier()))
    return total, upkeep


def _accrue_until(session: Session, player: Player, until: datetime) -> int:
    """Pay out the time elapsed since the last sync, at the rate stored on the player.

    Returns the net rubles moved. The clock only advances when something was actually
    paid: a player whose net income is 3 ₽/min would otherwise lose every ruble to
    `trunc()` if the client polled once a second.
    """
    net_per_min = int(player.income_rub_per_min) - int(player.upkeep_rub_per_min)
    if net_per_min == 0:
        player.income_synced_at = until
        return 0

    elapsed_minutes = (until - player.income_synced_at).total_seconds() / 60.0
    accrued = trunc(elapsed_minutes * net_per_min)
    if accrued == 0:
        # Less than one ruble has been earned. Leave the clock where it is so the
        # fraction is not silently dropped.
        return 0

    if accrued > 0:
        ledger.grant(session, player, "rub", accrued, "income_accrual")
    else:
        # Upkeep may empty a balance but never overdraw it.
        payable = min(-accrued, ledger.balance(player, "rub"))
        accrued = -payable
        if payable:
            ledger.spend(session, player, "rub", payable, "upkeep")

    player.income_synced_at = until
    return accrued


def accrue(session: Session, player: Player) -> int:
    return _accrue_until(session, player, utcnow())


def sync_player_income(session: Session, player: Player, bonuses: Bonuses | None = None) -> tuple[int, int]:
    """Settle what the old rate owed, then recompute the rate.

    Call after any change to the zoo, the player's items, or before any read of the
    balance. Accruing first is what makes the order correct: the stored rate is exactly
    the rate that applied over the elapsed period.
    """
    now = utcnow()
    # The cached rate is authoritative only until the first animal dies. Settle each
    # time segment at the rate that applied then, enqueue the death event in this same
    # transaction, and only afterwards compute the current rate. This closes the stale
    # cache window where an offline player could be paid through a dead animal's death.
    deaths = session.scalars(
        select(Animal)
        .where(
            Animal.player_id == player.id,
            Animal.removed_at.is_(None),
            Animal.dies_at > player.income_synced_at,
            Animal.dies_at <= now,
        )
        .order_by(Animal.dies_at.asc(), Animal.id.asc())
    ).all()
    for animal in deaths:
        _accrue_until(session, player, animal.dies_at)
        # A sub-ruble fraction cannot be carried across a rate change because the
        # schema stores whole-ruble balances. Do advance the boundary nevertheless;
        # otherwise a second death would still be paid at the first animal's rate.
        if player.income_synced_at < animal.dies_at:
            player.income_synced_at = animal.dies_at
        enqueue_animal_death(session, player, animal, reason="естественная смерть")

    _accrue_until(session, player, now)
    income, upkeep = calc_player_income(session, player.id, bonuses, now=now)
    player.income_rub_per_min = income
    player.upkeep_rub_per_min = upkeep
    return income, upkeep


def count_alive_animals(session: Session, player_id: int, season_id: int | None = None) -> int:
    stmt = select(Animal.id).where(Animal.player_id == player_id, alive_clause())
    if season_id is not None:
        stmt = stmt.where(Animal.season_id == season_id)
    return len(session.execute(stmt).all())


def alive_animals(session: Session, player_id: int, season_id: int) -> list[tuple[Animal, str | None]]:
    """Alive animals currently visible in the zoo, excluding an active expedition squad."""
    rows = list(
        session.execute(
            select(Animal, Locality.habitat)
            .outerjoin(Locality, Animal.locality_id == Locality.id)
            .where(
                Animal.player_id == player_id,
                Animal.season_id == season_id,
                alive_clause(),
                Animal.id.not_in(on_expedition_subquery()),
            )
            .order_by(Animal.acquired_at.desc())
        ).all()
    )
    return [(animal, habitat) for animal, habitat in rows]


def available_animals(session: Session, player_id: int, season_id: int) -> list[Animal]:
    """Alive and not already committed to an expedition."""
    return list(
        session.scalars(
            select(Animal)
            .where(
                Animal.player_id == player_id,
                Animal.season_id == season_id,
                alive_clause(),
                Animal.id.not_in(on_expedition_subquery()),
            )
            .order_by(Animal.acquired_at.desc())
        ).all()
    )
