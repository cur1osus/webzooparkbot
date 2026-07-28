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
import random
from collections import defaultdict
from datetime import datetime, timedelta
from math import trunc

from sqlalchemy import and_, func, or_, select
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
    OUTBREAK_CHANCE_PER_DAY,
    OUTBREAK_MIN_HEALTHY,
    OUTBREAK_MIN_LOCALITY_HEALTHY,
    OUTBREAK_SICKEN_FRACTION,
    development_effect_percent,
    locality_upkeep_discount,
    UPKEEP_BASE_PERCENT,
    UPKEEP_MAX_PERCENT,
    UPKEEP_PERCENT_PER_LOG10_ANIMALS,
    GeneTier,
    Rarity,
    gene_income_mult,
)
from api.app.zoopark.notifications import enqueue_animal_death_summaries, enqueue_disease_outbreak


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


def animal_base_income_rub_per_min(animal: Animal) -> int:
    """The intrinsic worth of an animal — genes and species rarity only, with no habitat
    bonus, no sickness penalty and no item multipliers. Breeding is priced off this so the
    fee cannot be gamed by moving an animal out of its habitat or letting it fall ill."""
    return animal_income_rub_per_min(
        survival=animal.gene_survival,  # type: ignore[arg-type]
        appearance=animal.gene_appearance,  # type: ignore[arg-type]
        size=animal.gene_size,  # type: ignore[arg-type]
        habitat_matches=False,
        is_sick=False,
        species_multiplier=1.0,
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

    sick_expression = Animal.sick_since.is_not(None)
    rows = session.execute(
        select(
            Animal.species_id,
            Animal.gene_survival,
            Animal.gene_appearance,
            Animal.gene_size,
            Animal.habitat,
            Locality.habitat,
            Locality.level,
            sick_expression,
            func.count(Animal.id),
        )
        .outerjoin(Locality, Animal.locality_id == Locality.id)
        .where(
            Animal.player_id == player_id,
            alive_clause(moment),
            Animal.id.not_in(on_expedition_subquery()),
        )
        .group_by(
            Animal.species_id,
            Animal.gene_survival,
            Animal.gene_appearance,
            Animal.gene_size,
            Animal.habitat,
            Locality.habitat,
            Locality.level,
            sick_expression,
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
    animal_count = 0
    for species_id, survival, appearance, size, animal_habitat, locality_habitat, locality_level, is_sick, count in rows:
        group_count = int(count)
        one_animal_income = animal_income_rub_per_min(
            survival=survival,
            appearance=appearance,
            size=size,
            habitat_matches=bool(locality_habitat) and locality_habitat == animal_habitat,
            is_sick=bool(is_sick),
            species_multiplier=active_bonuses.species_income_multiplier(species_id),
            species_rarity=SPECIES_BY_ID[species_id]["rarity"],
        )
        if clan_specialization == "specialist":
            rarity = SPECIES_BY_ID[species_id]["rarity"]
            if rarity in ("epic", "mythic", "legendary"):
                one_animal_income = round(one_animal_income * 1.5)
            elif rarity == "rare":
                one_animal_income = round(one_animal_income * 0.8)
        current_income = one_animal_income * group_count
        total += current_income
        upkeep_discount = locality_upkeep_discount(locality_level)
        level_discounted_income += current_income * upkeep_discount / 100
        levelled_locality_levels += max(int(locality_level or 0), 0) * group_count
        if locality_habitat and locality_habitat == animal_habitat:
            upkeep_discount += HABITAT_MATCH_UPKEEP_DISCOUNT
        locality_discounted_income += current_income * upkeep_discount / 100
        counts_by_species[species_id] = counts_by_species.get(species_id, 0) + group_count
        animal_count += group_count

    # After the 100× denomination rebase, truncating every multiplier is too coarse for
    # small zoos (e.g. 42 × 1.30 should become 55, not 54). Round each derived rate so
    # percentage bonuses remain visible at the new scale.
    total = round(total * active_bonuses.income_multiplier() * diversity_multiplier(list(counts_by_species.values())))
    if clan_specialization == "megapark":
        total = round(total * (1 + min(60, animal_count // 10) / 100))
    elif clan_specialization == "wild":
        total = round(total * (1 + len(counts_by_species) * 3 / 100))

    base_upkeep = upkeep_rub_per_min(total, animal_count)
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

    Time is counted, and the clock advanced, in whole seconds — never to `until` itself.
    MySQL's DATETIME holds no fraction, so writing `until` stored it rounded down and the
    next call measured from the rounded-down value: every poll billed the game for up to
    an extra second it had not lived through. `GET /api/me` accrues and has no rate limit,
    so a client polling in a loop minted money — measured at 258x the honest rate against
    a real MySQL. Whole seconds round-trip exactly, on either engine, so polling faster
    now earns exactly nothing extra.
    """
    net_per_min = int(player.income_rub_per_min) - int(player.upkeep_rub_per_min)
    elapsed = int((until - player.income_synced_at).total_seconds())
    if net_per_min == 0:
        player.income_synced_at += timedelta(seconds=max(elapsed, 0))
        return 0
    if elapsed <= 0:
        return 0

    accrued = trunc(elapsed / 60.0 * net_per_min)
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

    player.income_synced_at += timedelta(seconds=elapsed)
    return accrued


def accrue(session: Session, player: Player) -> int:
    return _accrue_until(session, player, utcnow())


def _maybe_disease_outbreak(session: Session, player: Player, now: datetime) -> bool:
    """Roll for a passive disease outbreak over the time elapsed since the last check.

    Frequency-independent: the per-check probability is `1 - (1 - daily_chance)^elapsed_days`,
    which compounds across any number of sub-intervals to the same total, so polling more
    often does not change how often outbreaks happen. When one fires it strikes a single
    locality — the more animals crowded there, the more fall ill.
    """
    last = player.outbreak_checked_at
    if last is None:
        # First check for this player: establish the anchor, strike nothing.
        player.outbreak_checked_at = now
        return False
    # Whole seconds, for the same reason the accrual counts them: the stored anchor carries
    # no fraction on MySQL, so advancing it to `now` handed the next check up to an extra
    # second of "elapsed" — and a client polling in a loop could rain outbreaks on itself.
    elapsed_seconds = int((now - last).total_seconds())
    if elapsed_seconds <= 0:
        return False
    player.outbreak_checked_at = last + timedelta(seconds=elapsed_seconds)
    elapsed_days = elapsed_seconds / 86_400.0

    chance = OUTBREAK_CHANCE_PER_DAY * (1 - development_effect_percent(player.vet_level) / 100)
    if chance <= 0:
        return False
    probability = 1 - (1 - chance) ** elapsed_days
    if random.random() >= probability:
        # The usual heartbeat path must not hydrate an entire 11k-animal zoo merely to
        # discover that the probability for this tiny interval did not fire.
        return False

    healthy = session.scalars(
        select(Animal).where(
            Animal.player_id == player.id,
            alive_clause(now),
            Animal.sick_since.is_(None),
            Animal.id.not_in(on_expedition_subquery()),
        )
    ).all()
    if len(healthy) < OUTBREAK_MIN_HEALTHY:
        return False

    by_locality: dict[int | None, list[Animal]] = defaultdict(list)
    for animal in healthy:
        by_locality[animal.locality_id].append(animal)
    candidates = [group for group in by_locality.values() if len(group) >= OUTBREAK_MIN_LOCALITY_HEALTHY]
    if not candidates:
        return False

    struck = random.choice(candidates)
    count = max(1, math.ceil(len(struck) * OUTBREAK_SICKEN_FRACTION))
    for animal in random.sample(struck, min(count, len(struck))):
        animal.sick_since = now
    enqueue_disease_outbreak(session, player, count=count, at=now)
    return True


def _settle_player_income(
    session: Session,
    player: Player,
    bonuses: Bonuses | None,
    *,
    force_recalculate: bool,
) -> tuple[int, int]:
    """Settle the cached rate and rescan the zoo only when it can have changed."""
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
            # Equality matters on MySQL's second-precision DATETIME. An animal whose death
            # lands exactly on the accrual anchor still invalidates the cached rate.
            Animal.dies_at >= player.income_synced_at,
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
    enqueue_animal_death_summaries(session, player, deaths, reason="естественная смерть")

    _accrue_until(session, player, now)
    outbreak = _maybe_disease_outbreak(session, player, now)
    if not force_recalculate and not deaths and not outbreak:
        return player.income_rub_per_min, player.upkeep_rub_per_min

    income, upkeep = calc_player_income(session, player.id, bonuses, now=now)
    player.income_rub_per_min = income
    player.upkeep_rub_per_min = upkeep
    return income, upkeep


def settle_player_income(session: Session, player: Player, bonuses: Bonuses | None = None) -> tuple[int, int]:
    """Accrue balances and passive events without an unconditional full-zoo scan."""
    return _settle_player_income(session, player, bonuses, force_recalculate=False)


def sync_player_income(session: Session, player: Player, bonuses: Bonuses | None = None) -> tuple[int, int]:
    """Settle the old rate and rebuild it after a zoo/item mutation."""
    return _settle_player_income(session, player, bonuses, force_recalculate=True)


def sync_active_player_income(session: Session) -> int:
    """Advance passive events for every active player during a worker scan.

    The web request path used to be the only caller of ``sync_player_income``. That made
    disease rolls and natural-death notifications wait until the player opened the app.
    The notification worker calls this periodically so the same authoritative transition
    happens while the player is offline. Cached rates are only rebuilt when that pass finds
    a death or outbreak. The row lock keeps it from racing a foreground mutation;
    notification dedupe keys make a concurrent worker safe as well.
    """
    players = session.scalars(
        select(Player)
        .where(Player.status == "active")
        .order_by(Player.id.asc())
        .with_for_update()
    ).all()
    for player in players:
        settle_player_income(session, player)
    return len(players)


def count_alive_animals(session: Session, player_id: int, season_id: int | None = None) -> int:
    stmt = select(func.count(Animal.id)).where(Animal.player_id == player_id, alive_clause())
    if season_id is not None:
        stmt = stmt.where(Animal.season_id == season_id)
    return int(session.scalar(stmt) or 0)


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


def breeding_animals(session: Session, player_id: int, season_id: int, today) -> list[tuple[Animal, str | None]]:
    """Ready animals from species that have at least two ready members.

    Filtering pairable species in SQL avoids shipping the rest of a large zoo
    to the lab. The grouped subquery also makes the old client-side pair
    search unnecessary.
    """
    ready = (
        Animal.player_id == player_id,
        Animal.season_id == season_id,
        alive_clause(),
        Animal.id.not_in(on_expedition_subquery()),
        or_(Animal.last_bred_on.is_(None), Animal.last_bred_on != today),
    )
    pairable_species = (
        select(Animal.species_id)
        .where(*ready)
        .group_by(Animal.species_id)
        .having(func.count(Animal.id) >= 2)
        .scalar_subquery()
    )
    return list(
        session.execute(
            select(Animal, Locality.habitat)
            .outerjoin(Locality, Animal.locality_id == Locality.id)
            .where(*ready, Animal.species_id.in_(pairable_species))
            .order_by(Animal.acquired_at.desc())
        ).all()
    )
