"""Packs, localities, breeding and expeditions — the GDD's core loop."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from random import SystemRandom
from typing import cast

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import (
    Animal,
    BreedingAttempt,
    Expedition,
    ExpeditionMember,
    Locality,
    PackOpening,
    Player,
    utcnow,
)
from api.app.schemas.progression import AssignLocalityBody, BreedBody, BuyLocalityBody, StartExpeditionBody, UpgradeLocalityBody
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import ledger
from api.app.zoopark.catalog import (
    EXPEDITION_SICK_CHANCE,
    EXPEDITION_SQUAD_MAX,
    EXPEDITION_SQUAD_MIN,
    EXPEDITION_WILD_SCALE,
    EXPEDITIONS,
    GENE_ROLL_WEIGHTS,
    GENE_TIERS,
    HABITATS,
    LIFESPAN_DAYS,
    LOCALITY_BASE_PRICE_RUB,
    LOCALITY_PRICE_GROWTH,
    locality_upkeep_discount,
    locality_upgrade_cost_rub,
    MAX_LOCALITIES,
    PackTier,
    SPECIES_IDS_BY_RARITY,
    SPECIES_BY_ID,
    SPECIES_RARITY_WEIGHTS,
    BREED_WORSE_GENE_CHANCE,
    BREED_TIER_INDEX,
    GeneTier,
    Habitat,
    ANIMAL_NAME_POOL,
    breed_success_rate,
    combat_power,
    DAILY_GIFT_TIER_WEIGHTS,
    development_effect_percent,
    PACK_TIER_ORDER,
    pack_price_usd_for_tier,
    pack_reward_range,
)
from api.app.zoopark.income import (
    alive_clause,
    available_animals,
    on_expedition_subquery,
    sync_player_income,
)
from api.app.zoopark.notifications import enqueue_animal_death, enqueue_expedition_finished
from api.app.zoopark.profile import animal_payload, get_player
from api.app.zoopark.season import ensure_player_season

random = SystemRandom()


# ─── Rolling an animal ────────────────────────────────────────────────────────


def roll_gene(weights: tuple[float, float, float] = GENE_ROLL_WEIGHTS) -> GeneTier:
    return random.choices(GENE_TIERS, weights=weights)[0]


def roll_genes(weights: tuple[float, float, float] = GENE_ROLL_WEIGHTS) -> dict[str, GeneTier]:
    return {
        "gene_survival": roll_gene(weights),
        "gene_reproduction": roll_gene(weights),
        "gene_appearance": roll_gene(weights),
        "gene_size": roll_gene(weights),
    }


def roll_habitat() -> Habitat:
    return random.choice(HABITATS)


def roll_animal_name() -> str:
    return random.choice(ANIMAL_NAME_POOL)


def roll_daily_gift_tier() -> str:
    """The free daily gift's tier: usually rare, rarely legendary/mythic."""
    tiers = list(DAILY_GIFT_TIER_WEIGHTS)
    return random.choices(tiers, weights=[DAILY_GIFT_TIER_WEIGHTS[t] for t in tiers])[0]


def daily_gift_odds() -> list[dict]:
    """Per-tier drop chance of the free gift, as whole-percent ints for display."""
    total = sum(DAILY_GIFT_TIER_WEIGHTS.values())
    return [
        {"tier": tier, "percent": round(weight / total * 100)}
        for tier, weight in DAILY_GIFT_TIER_WEIGHTS.items()
    ]


def roll_species_id() -> int:
    """Roll a species independently from its genes; rarity affects the species income
    multiplier while the genes still determine most of the animal's value."""
    rarity = random.choices(list(SPECIES_RARITY_WEIGHTS), weights=list(SPECIES_RARITY_WEIGHTS.values()))[0]
    return random.choice(SPECIES_IDS_BY_RARITY[rarity])


def dies_at_for(survival: GeneTier, now: datetime | None = None) -> datetime:
    return (now or utcnow()) + timedelta(days=LIFESPAN_DAYS[survival])


def create_animal(
    session: Session,
    *,
    player_id: int,
    season_id: int,
    origin: str,
    genes: dict[str, GeneTier],
    habitat: Habitat,
    species_id: int | None = None,
    parent_a_id: int | None = None,
    parent_b_id: int | None = None,
) -> Animal:
    now = utcnow()
    animal = Animal(
        player_id=player_id,
        season_id=season_id,
        species_id=species_id or roll_species_id(),
        name=roll_animal_name(),
        habitat=habitat,
        origin=origin,
        acquired_at=now,
        dies_at=dies_at_for(genes["gene_survival"], now),
        parent_a_id=parent_a_id,
        parent_b_id=parent_b_id,
        **genes,
    )
    session.add(animal)
    session.flush()
    return animal


# ─── Packs ────────────────────────────────────────────────────────────────────


def _utc_day_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _openings_today(session: Session, player_id: int, season_id: int) -> list[PackOpening]:
    start, end = _utc_day_bounds(utcnow())
    return list(session.scalars(
        select(PackOpening).where(
            PackOpening.player_id == player_id,
            PackOpening.season_id == season_id,
            PackOpening.opened_at >= start,
            PackOpening.opened_at < end,
        )
    ).all())


def _paid_tiers_today(openings: list[PackOpening]) -> set[str]:
    """Tiers the player has bought (price > 0) today — these unlock the next tier."""
    return {o.tier for o in openings if int(o.price_paid_usd) > 0}


def _paid_pack_count(session: Session, player_id: int, season_id: int) -> int:
    """Number of paid packs opened by this player during this season."""
    count = session.scalar(
        select(func.count())
        .select_from(PackOpening)
        .where(
            PackOpening.player_id == player_id,
            PackOpening.season_id == season_id,
            PackOpening.price_paid_usd > 0,
        )
    )
    return int(count or 0)


def _gift_claimed_today(openings: list[PackOpening]) -> bool:
    """The free daily gift is recorded as a price-0 opening."""
    return any(int(o.price_paid_usd) == 0 for o in openings)


def tier_unlocked(tier: str, paid_tiers: set[str]) -> bool:
    """Rare is always open; every higher tier unlocks once the one below it is bought."""
    idx = PACK_TIER_ORDER.index(tier)
    if idx == 0:
        return True
    return PACK_TIER_ORDER[idx - 1] in paid_tiers


def list_available_animals(tg_id: int) -> dict:
    """Alive, and not already committed to an expedition.

    Breeding used to read this out of `GET /api/packs/info`, which had no business
    knowing about it.
    """
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)
        bonuses = bonuses_module.load(session, player.id)
        animals = available_animals(session, player.id, season.id)
        session.commit()
        return {"animals": [animal_payload(a, None, bonuses) for a in animals]}


def packs_info(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)
        openings = _openings_today(session, player.id, season.id)
        paid_tiers = _paid_tiers_today(openings)
        paid_pack_count = _paid_pack_count(session, player.id, season.id)
        pack_discount = bonuses_module.load(session, player.id).pack_discount_multiplier()
        session.commit()
        tiers = [
            {
                "tier": tier,
                "price": pack_price_usd_for_tier(tier, pack_discount, paid_pack_count),
                "unlocked": tier_unlocked(tier, paid_tiers),
                "reward_range": pack_reward_range(tier),
            }
            for tier in PACK_TIER_ORDER
        ]
        return {
            "gift_available": not _gift_claimed_today(openings),
            "gift_odds": daily_gift_odds(),
            "tiers": tiers,
        }


def open_pack(tg_id: int, tier: str | None = None) -> dict:
    """Open a pack. `tier=None` opens the free daily gift (random tier, once a day); a tier
    name buys that tier — allowed only if it is unlocked, and repeatable with a 5% daily
    price increase after every paid opening."""
    with get_session() as session:
        # The row lock serialises opening so the daily-gift / unlock checks can't race.
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)
        season = ensure_player_season(session, player)

        openings = _openings_today(session, player.id, season.id)
        bonuses = bonuses_module.load(session, player.id)
        if tier is None:
            # The free daily gift: one per day, random tier weighted toward rare.
            if _gift_claimed_today(openings):
                raise HTTPException(400, "Ежедневный подарок уже получен сегодня")
            tier = roll_daily_gift_tier()
            price = 0
        else:
            if tier not in PACK_TIER_ORDER:
                raise HTTPException(400, "Неизвестный тир пака")
            if not tier_unlocked(tier, _paid_tiers_today(openings)):
                raise HTTPException(400, "Этот тир ещё не открыт — сначала открой предыдущий")
            price = pack_price_usd_for_tier(
                tier,
                bonuses.pack_discount_multiplier(),
                _paid_pack_count(session, player.id, season.id),
            )
        tier = cast(PackTier, tier)
        rewards = pack_reward_range(tier)

        if price > 0:
            ledger.spend(session, player, "usd", price, "pack_open")

        # Genes always roll 40/40/20 and habitats stay uniform. Higher pack tiers add
        # reward quantity, while each animal keeps the same independent genetics roll.
        animals = [
            create_animal(
                session,
                player_id=player.id,
                season_id=season.id,
                origin="pack",
                genes=roll_genes(),
                habitat=roll_habitat(),
            )
            for _ in range(random.randint(*rewards["animals"]))
        ]
        opening = PackOpening(
            player_id=player.id,
            season_id=season.id,
            animal_id=animals[0].id,
            tier=tier,
            # Packs are now paid in dollars; this write-only audit column keeps its legacy
            # name but records the dollar price paid.
            price_paid_usd=price,
        )
        session.add(opening)
        session.flush()
        rub_reward = random.randint(*rewards["rub"])
        usd_reward = random.randint(*rewards["usd"])
        ledger.grant(session, player, "rub", rub_reward, "pack_reward", ref_table="pack_openings", ref_id=opening.id)
        ledger.grant(session, player, "usd", usd_reward, "pack_reward", ref_table="pack_openings", ref_id=opening.id)

        sync_player_income(session, player, bonuses)
        animal_payloads = [animal_payload(animal, None, bonuses) for animal in animals]
        # Recompute today's state so the client can refresh unlocks/gift without a round trip.
        openings_after = _openings_today(session, player.id, season.id)
        paid_after = _paid_tiers_today(openings_after)
        was_gift = price == 0
        result = {
            "ok": True,
            "tier": tier,
            "is_gift": was_gift,
            "price_paid": price,
            "new_rub": ledger.balance(player, "rub"),
            "new_usd": ledger.balance(player, "usd"),
            "gift_available": not _gift_claimed_today(openings_after),
            "unlocked_tiers": [t for t in PACK_TIER_ORDER if tier_unlocked(t, paid_after)],
            "rewards": {"rub": rub_reward, "usd": usd_reward},
            "animals": animal_payloads,
            # Kept until all deployed clients use the bundle response.
            "animal": animal_payloads[0],
        }
        session.commit()
        return result


# ─── Localities ───────────────────────────────────────────────────────────────


def locality_price_rub(owned_count: int, discount_multiplier: float = 1.0) -> int:
    """GDD §5: the first is free, then Базовая цена × 1.5^(кол-во купленных)."""
    if owned_count == 0:
        return 0
    base = LOCALITY_BASE_PRICE_RUB * (LOCALITY_PRICE_GROWTH ** (owned_count - 1))
    return int(base * discount_multiplier)


def ensure_first_locality(session: Session, player_id: int, season_id: int) -> None:
    """GDD §5: the first locality is free and random. Granted at registration; this stays
    idempotent so a player who registered before it existed still gets one."""
    existing = session.scalars(
        select(Locality.id).where(Locality.player_id == player_id, Locality.season_id == season_id)
    ).all()
    if existing:
        return
    try:
        with session.begin_nested():
            session.add(
                Locality(
                    player_id=player_id,
                    season_id=season_id,
                    habitat=roll_habitat(),
                    price_paid_rub=0,
                )
            )
    except IntegrityError:
        pass


def list_localities(tg_id: int) -> dict:
    with get_session() as session:
        # This endpoint grants the first locality lazily. Lock the player before the
        # check so two simultaneous first-page loads cannot roll two free localities.
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)
        ensure_first_locality(session, player.id, season.id)

        localities = session.scalars(
            select(Locality)
            .where(Locality.player_id == player.id, Locality.season_id == season.id)
            .order_by(Locality.purchased_at.asc(), Locality.id.asc())
        ).all()
        bonuses = bonuses_module.load(session, player.id)
        animals = available_animals(session, player.id, season.id)
        session.commit()

        by_id = {loc.id: loc for loc in localities}
        buckets: dict[int | None, list[Animal]] = {loc.id: [] for loc in localities}
        buckets[None] = []
        for animal in animals:
            buckets[animal.locality_id if animal.locality_id in by_id else None].append(animal)

        owned = len(localities)
        return {
            "localities": [
                {
                    "id": loc.id,
                    "habitat": loc.habitat,
                    "level": loc.level,
                    "upkeep_discount_percent": locality_upkeep_discount(loc.level),
                    "next_upkeep_discount_percent": locality_upkeep_discount(loc.level + 1) if locality_upgrade_cost_rub(loc.level) is not None else None,
                    "upgrade_cost_rub": locality_upgrade_cost_rub(loc.level),
                    "animals": [animal_payload(a, loc.habitat, bonuses) for a in buckets[loc.id]],
                }
                for loc in localities
            ],
            "unassigned": [animal_payload(a, None, bonuses) for a in buckets[None]],
            "next_price": locality_price_rub(owned, bonuses.locality_discount_multiplier()) if owned < MAX_LOCALITIES else None,
            "habitats_taken": [loc.habitat for loc in localities],
            "max_localities": MAX_LOCALITIES,
        }


def buy_locality(tg_id: int, body: BuyLocalityBody) -> dict:
    if body.habitat not in HABITATS:
        raise HTTPException(400, "Неверная среда обитания")

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)
        season = ensure_player_season(session, player)

        localities = session.scalars(
            select(Locality).where(Locality.player_id == player.id, Locality.season_id == season.id)
        ).all()
        if len(localities) >= MAX_LOCALITIES:
            raise HTTPException(400, f"Достигнут максимум местностей ({MAX_LOCALITIES})")
        if any(loc.habitat == body.habitat for loc in localities):
            raise HTTPException(400, "Эта местность уже открыта")

        bonuses = bonuses_module.load(session, player.id)
        price = locality_price_rub(len(localities), bonuses.locality_discount_multiplier())
        if price > 0:
            ledger.spend(session, player, "rub", price, "locality_buy")

        locality = Locality(
            player_id=player.id,
            season_id=season.id,
            habitat=body.habitat,
            price_paid_rub=price,
        )
        session.add(locality)
        try:
            session.flush()
        except IntegrityError as exc:
            raise HTTPException(400, "Эта местность уже открыта") from exc

        result = {
            "ok": True,
            "id": locality.id,
            "habitat": locality.habitat,
            "price_paid": price,
            "new_rub": ledger.balance(player, "rub"),
        }
        session.commit()
        return result


def upgrade_locality(tg_id: int, body: UpgradeLocalityBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)
        locality = session.scalars(
            select(Locality)
            .where(
                Locality.id == body.locality_id,
                Locality.player_id == player.id,
                Locality.season_id == season.id,
            )
            .with_for_update()
        ).first()
        if locality is None:
            raise HTTPException(404, "Местность не найдена")
        cost = locality_upgrade_cost_rub(locality.level)
        if cost is None:
            raise HTTPException(400, "Местность уже улучшена до максимума")
        ledger.spend(session, player, "rub", cost, "locality_upgrade")
        locality.level += 1
        sync_player_income(session, player)
        result = {
            "ok": True,
            "id": locality.id,
            "level": locality.level,
            "upkeep_discount_percent": locality_upkeep_discount(locality.level),
            "next_upkeep_discount_percent": locality_upkeep_discount(locality.level + 1) if locality_upgrade_cost_rub(locality.level) is not None else None,
            "upgrade_cost_rub": locality_upgrade_cost_rub(locality.level),
            "new_rub": ledger.balance(player, "rub"),
        }
        session.commit()
        return result


def assign_locality(tg_id: int, body: AssignLocalityBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)

        animal = session.scalars(
            select(Animal).where(
                Animal.id == body.animal_id,
                Animal.player_id == player.id,
                Animal.season_id == season.id,
                alive_clause(),
            )
        ).first()
        if not animal:
            raise HTTPException(404, "Животное не найдено")

        if body.locality_id is not None:
            locality = session.scalars(
                select(Locality).where(
                    Locality.id == body.locality_id,
                    Locality.player_id == player.id,
                    Locality.season_id == season.id,
                )
            ).first()
            if not locality:
                raise HTTPException(404, "Местность не найдена")

        animal.locality_id = body.locality_id
        # Moving an animal into (or out of) its habitat changes income by 50%.
        sync_player_income(session, player)
        result = {"ok": True, "income_rub_per_min": player.income_rub_per_min}
        session.commit()
        return result


# ─── Breeding ─────────────────────────────────────────────────────────────────


def inherit_gene(a: GeneTier, b: GeneTier, worse_gene_chance: float = BREED_WORSE_GENE_CHANCE) -> GeneTier:
    """GDD §6: identical genes pass through; otherwise the worse one wins 60% of the time."""
    if a == b:
        return a
    worse, better = (a, b) if BREED_TIER_INDEX[a] < BREED_TIER_INDEX[b] else (b, a)
    return worse if random.random() < worse_gene_chance else better


def inheritance_source(child: GeneTier, parent_a: GeneTier, parent_b: GeneTier) -> str:
    if parent_a == parent_b:
        return "both"
    if child == parent_a:
        return "parent_a"
    return "parent_b"


def breed(tg_id: int, body: BreedBody) -> dict:
    if body.animal_id_1 == body.animal_id_2:
        raise HTTPException(400, "Нельзя скрещивать животное с самим собой")

    with get_session() as session:
        # Lock the player so two parallel calls cannot both pass the `last_bred_on` check.
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)

        today = utcnow().date()
        parents = session.scalars(
            select(Animal)
            .where(
                Animal.id.in_([body.animal_id_1, body.animal_id_2]),
                Animal.player_id == player.id,
                Animal.season_id == season.id,
                alive_clause(),
                Animal.id.not_in(on_expedition_subquery()),
            )
            .with_for_update()
        ).all()
        by_id = {a.id: a for a in parents}
        if len(by_id) != 2:
            raise HTTPException(404, "Одно или оба животных недоступны")

        parent_a, parent_b = by_id[body.animal_id_1], by_id[body.animal_id_2]
        if parent_a.species_id != parent_b.species_id:
            raise HTTPException(400, "Скрещивать можно только животных одного вида")
        for parent in (parent_a, parent_b):
            if parent.last_bred_on == today:
                raise HTTPException(400, "Одно из животных уже скрещивалось сегодня")

        genetics_bonus = development_effect_percent(player.genetics_level)
        rate = min(0.95, breed_success_rate(parent_a.gene_reproduction, parent_b.gene_reproduction) + genetics_bonus / 100)  # type: ignore[arg-type]
        worse_gene_chance = max(0.48, BREED_WORSE_GENE_CHANCE - genetics_bonus / 100)
        succeeded = random.random() < rate
        parent_a.last_bred_on = today
        parent_b.last_bred_on = today

        child = None
        inherited_genes = None
        if succeeded:
            genes = {
                "gene_survival": inherit_gene(parent_a.gene_survival, parent_b.gene_survival, worse_gene_chance),  # type: ignore[arg-type]
                "gene_reproduction": inherit_gene(parent_a.gene_reproduction, parent_b.gene_reproduction, worse_gene_chance),  # type: ignore[arg-type]
                "gene_appearance": inherit_gene(parent_a.gene_appearance, parent_b.gene_appearance, worse_gene_chance),  # type: ignore[arg-type]
                "gene_size": inherit_gene(parent_a.gene_size, parent_b.gene_size, worse_gene_chance),  # type: ignore[arg-type]
            }
            child = create_animal(
                session,
                player_id=player.id,
                season_id=season.id,
                origin="breeding",
                genes=genes,
                # GDD §6: the child's habitat comes from one parent, 50/50.
                habitat=cast(Habitat, random.choice([parent_a.habitat, parent_b.habitat])),
                species_id=random.choice([parent_a.species_id, parent_b.species_id]),
                parent_a_id=parent_a.id,
                parent_b_id=parent_b.id,
            )
            inherited_genes = []
            for gene, child_value, parent_a_value, parent_b_value in (
                ("survival", child.gene_survival, parent_a.gene_survival, parent_b.gene_survival),
                ("reproduction", child.gene_reproduction, parent_a.gene_reproduction, parent_b.gene_reproduction),
                ("appearance", child.gene_appearance, parent_a.gene_appearance, parent_b.gene_appearance),
                ("size_trait", child.gene_size, parent_a.gene_size, parent_b.gene_size),
            ):
                source = inheritance_source(
                    cast(GeneTier, child_value),
                    cast(GeneTier, parent_a_value),
                    cast(GeneTier, parent_b_value),
                )
                inherited_genes.append(
                    {
                        "gene": gene,
                        "value": child_value,
                        "source": source,
                        "source_name": "Оба родителя" if source == "both" else parent_a.name if source == "parent_a" else parent_b.name,
                        "parent_a_name": parent_a.name,
                        "parent_b_name": parent_b.name,
                        "parent_a_value": parent_a_value,
                        "parent_b_value": parent_b_value,
                    }
                )

        session.add(
            BreedingAttempt(
                player_id=player.id,
                season_id=season.id,
                parent_a_id=parent_a.id,
                parent_b_id=parent_b.id,
                child_id=child.id if child else None,
                success_rate_pct=int(rate * 100),
                succeeded=succeeded,
            )
        )

        bonuses = bonuses_module.load(session, player.id)
        sync_player_income(session, player, bonuses)
        result = {
            "ok": True,
            "success": succeeded,
            "rate": rate,
            "animal": animal_payload(child, None, bonuses) if child else None,
            "inherited_genes": inherited_genes,
        }
        session.commit()
        return result


# ─── Expeditions ──────────────────────────────────────────────────────────────


def roll_wild_gene(weights: tuple[float, float, float]) -> GeneTier:
    return random.choices(GENE_TIERS, weights=weights)[0]


def wild_encounter(habitat: Habitat) -> tuple[dict[str, GeneTier], int]:
    """The beast the squad meets. Its genes follow the habitat's Плохое/Обычное/Хорошее
    split (GDD §7) and become the captured animal's genes on victory."""
    weights = EXPEDITIONS[habitat]["gene_weights"]
    genes = {
        "gene_survival": roll_wild_gene(weights),
        "gene_reproduction": roll_wild_gene(weights),
        "gene_appearance": roll_wild_gene(weights),
        "gene_size": roll_wild_gene(weights),
    }
    raw = combat_power(genes["gene_survival"], genes["gene_appearance"], genes["gene_size"])
    return genes, int(raw * EXPEDITION_WILD_SCALE)


def squad_power(animals: list[Animal]) -> int:
    return sum(
        combat_power(
            cast(GeneTier, a.gene_survival),
            cast(GeneTier, a.gene_appearance),
            cast(GeneTier, a.gene_size),
        )
        for a in animals
    )


def _resolve(session: Session, expedition: Expedition, player: Player, season_id: int) -> dict:
    squad = list(
        session.scalars(
            select(Animal)
            .join(ExpeditionMember, ExpeditionMember.animal_id == Animal.id)
            .where(ExpeditionMember.expedition_id == expedition.id)
        ).all()
    )
    habitat: Habitat = expedition.locality.habitat  # type: ignore[assignment]
    genes, wild_power = wild_encounter(habitat)
    wild_species_id = roll_species_id()
    wild_species = SPECIES_BY_ID[wild_species_id]
    power = squad_power(squad)

    now = utcnow()
    # The client names the size gene `size_trait` everywhere else; keep it one name.
    wild_payload: dict[str, object] = {key.removeprefix("gene_"): value for key, value in genes.items()}
    wild_payload["size_trait"] = wild_payload.pop("size")
    wild_payload.update(
        {
            "species_code": wild_species["code"],
            "species_name": wild_species["name"],
            "species_emoji": wild_species["emoji"],
            "species_rarity": wild_species["rarity"],
        }
    )
    result: dict = {
        "squad_power": power,
        "wild_power": wild_power,
        "wild": wild_payload,
        "habitat": habitat,
    }

    # GDD §7: "Сила отряда ≥ сила дикого → Захват!". The beast is scaled by
    # EXPEDITION_WILD_SCALE so that the comparison can actually go either way.
    if power >= wild_power:
        captured = create_animal(
            session,
            player_id=player.id,
            season_id=season_id,
            origin="expedition",
            genes=genes,
            habitat=habitat,
            species_id=wild_species_id,
        )
        expedition.outcome = "victory"
        result["outcome"] = "victory"
        result["captured_animal_id"] = captured.id
    else:
        expedition.outcome = "defeat"
        result["outcome"] = "defeat"
        alive = [a for a in squad if a.removed_at is None]
        victim = random.choice(alive) if alive else None
        if victim is not None:
            victim.removed_at = now
            victim.removal_reason = "expedition_loss"
            victim.sick_since = None
            enqueue_animal_death(session, player, victim, reason="expedition_loss")
        result["killed_animal_id"] = victim.id if victim else None
        result["sick_animal_ids"] = _wound_survivors(alive, victim, now, player.vet_level)

    expedition.resolved_at = now
    expedition.result_json = json.dumps(result, ensure_ascii=False)
    enqueue_expedition_finished(session, player, expedition, result)
    return result


def _wound_survivors(squad: list[Animal], victim: Animal | None, now: datetime, vet_level: int = 0) -> list[int]:
    wounded: list[int] = []
    sickness_chance = EXPEDITION_SICK_CHANCE * (1 - development_effect_percent(vet_level) / 100)
    for animal in squad:
        if (victim is not None and animal.id == victim.id) or animal.sick_since is not None:
            continue
        if random.random() >= sickness_chance:
            continue
        animal.sick_since = now
        wounded.append(animal.id)
    return wounded


def _open_expedition(session: Session, player_id: int, season_id: int) -> Expedition | None:
    return session.scalars(
        select(Expedition)
        .where(
            Expedition.player_id == player_id,
            Expedition.season_id == season_id,
            (Expedition.resolved_at.is_(None)) | (Expedition.acknowledged_at.is_(None)),
        )
        .order_by(Expedition.started_at.desc())
        .limit(1)
    ).first()


def get_expeditions(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)
        bonuses = bonuses_module.load(session, player.id)

        localities = session.scalars(
            select(Locality)
            .where(Locality.player_id == player.id, Locality.season_id == season.id)
            .order_by(Locality.purchased_at.asc())
        ).all()

        expedition = _open_expedition(session, player.id, season.id)
        active = None
        if expedition is not None:
            # Reading never resolves: two concurrent GETs used to roll the outcome twice
            # and hand out two reward animals.
            squad = session.scalars(
                select(Animal)
                .join(ExpeditionMember, ExpeditionMember.animal_id == Animal.id)
                .where(ExpeditionMember.expedition_id == expedition.id)
            ).all()
            result = json.loads(expedition.result_json) if expedition.result_json else None
            if result and result.get("captured_animal_id"):
                captured = session.get(Animal, result["captured_animal_id"])
                if captured:
                    result["captured_animal"] = animal_payload(captured, None, bonuses)
            active = {
                "id": expedition.id,
                "habitat": expedition.locality.habitat,
                "started_at": expedition.started_at.isoformat(),
                "ends_at": expedition.ends_at.isoformat(),
                "status": "active" if expedition.resolved_at is None else "finished",
                "animals": [animal_payload(a, None, bonuses) for a in squad],
                "result": result,
            }

        squad_pool = available_animals(session, player.id, season.id)
        session.commit()
        return {
            "active": active,
            "localities": [{"id": loc.id, "habitat": loc.habitat} for loc in localities],
            "available_animals": [animal_payload(a, None, bonuses) for a in squad_pool],
            "expedition_minutes": {habitat: spec["minutes"] for habitat, spec in EXPEDITIONS.items()},
            "squad_min": EXPEDITION_SQUAD_MIN,
            "squad_max": EXPEDITION_SQUAD_MAX,
        }


def start_expedition(tg_id: int, body: StartExpeditionBody) -> dict:
    animal_ids = list(dict.fromkeys(body.animal_ids))
    if len(animal_ids) != len(body.animal_ids):
        raise HTTPException(400, "Животное указано дважды")
    if not (EXPEDITION_SQUAD_MIN <= len(animal_ids) <= EXPEDITION_SQUAD_MAX):
        raise HTTPException(400, f"Отряд: {EXPEDITION_SQUAD_MIN}–{EXPEDITION_SQUAD_MAX} животных")

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)

        if _open_expedition(session, player.id, season.id) is not None:
            raise HTTPException(400, "Уже есть активная или незавершённая экспедиция")

        locality = session.scalars(
            select(Locality).where(
                Locality.id == body.locality_id,
                Locality.player_id == player.id,
                Locality.season_id == season.id,
            )
        ).first()
        if not locality:
            raise HTTPException(404, "Местность не найдена")

        squad = session.scalars(
            select(Animal).where(
                Animal.id.in_(animal_ids),
                Animal.player_id == player.id,
                Animal.season_id == season.id,
                alive_clause(),
                Animal.id.not_in(on_expedition_subquery()),
            )
        ).all()
        if len(squad) != len(animal_ids):
            raise HTTPException(400, "Некоторые животные недоступны")

        now = utcnow()
        expedition = Expedition(
            player_id=player.id,
            season_id=season.id,
            locality_id=locality.id,
            started_at=now,
            ends_at=now + timedelta(minutes=EXPEDITIONS[locality.habitat]["minutes"]),  # type: ignore[index]
        )
        session.add(expedition)
        try:
            session.flush()
        except IntegrityError as exc:
            # `uq_expeditions_one_active` — someone started one between the check and here.
            raise HTTPException(400, "Уже есть активная экспедиция") from exc

        for animal in squad:
            session.add(ExpeditionMember(expedition_id=expedition.id, animal_id=animal.id))

        bonuses = bonuses_module.load(session, player.id)
        # Animals on an expedition earn nothing (GDD §7), so income drops immediately.
        sync_player_income(session, player, bonuses)
        result = {
            "ok": True,
            "expedition": {
                "id": expedition.id,
                "habitat": locality.habitat,
                "started_at": expedition.started_at.isoformat(),
                "ends_at": expedition.ends_at.isoformat(),
                "status": "active",
                "animals": [animal_payload(a, None, bonuses) for a in squad],
                "result": None,
            },
        }
        session.commit()
        return result


def finish_expedition(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)

        # FOR UPDATE plus the `resolved_at` re-check make finishing idempotent: the second
        # caller blocks, then sees the expedition already resolved.
        expedition = session.scalars(
            select(Expedition)
            .where(
                Expedition.player_id == player.id,
                Expedition.season_id == season.id,
                Expedition.resolved_at.is_(None),
            )
            .order_by(Expedition.started_at.desc())
            .with_for_update()
            .limit(1)
        ).first()
        if not expedition:
            raise HTTPException(400, "Нет активной экспедиции")
        if utcnow() < expedition.ends_at:
            raise HTTPException(400, "Экспедиция ещё не завершена")

        result = _resolve(session, expedition, player, season.id)

        bonuses = bonuses_module.load(session, player.id)
        sync_player_income(session, player, bonuses)
        if result.get("captured_animal_id"):
            captured = session.get(Animal, result["captured_animal_id"])
            if captured:
                result["captured_animal"] = animal_payload(captured, None, bonuses)

        session.commit()
        return {"ok": True, "result": result}


def dismiss_expedition(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)
        expedition = session.scalars(
            select(Expedition)
            .where(
                Expedition.player_id == player.id,
                Expedition.season_id == season.id,
                Expedition.resolved_at.is_not(None),
                Expedition.acknowledged_at.is_(None),
            )
            .with_for_update()
        ).first()
        if expedition is not None:
            expedition.acknowledged_at = utcnow()
        session.commit()
        return {"ok": True}
