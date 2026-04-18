from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
import random

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.app.core.errors import AppError
from api.app.models.enums import AnimalStatus, ExpeditionOutcome, HabitatType
from api.app.models.expedition import Expedition, ExpeditionPartyMember
from api.app.models.player_season import PlayerSeason
from api.app.services.logic import (
    animal_combat_power,
    create_expedition_animal,
    ensure_utc,
    expedition_duration,
    party_combat_power,
    to_storage_datetime,
)


PENDING_OUTCOME = ExpeditionOutcome.PENDING


def active_expedition(db: Session, profile: PlayerSeason) -> Expedition | None:
    return db.scalar(
        select(Expedition)
        .options(selectinload(Expedition.party_members).selectinload(ExpeditionPartyMember.animal))
        .where(Expedition.player_season_id == profile.id, Expedition.outcome == PENDING_OUTCOME)
        .order_by(Expedition.started_at.asc())
        .limit(1)
    )


def start_expedition(db: Session, profile: PlayerSeason, target_terrain_type: HabitatType, animal_ids: list[str], now: datetime):
    if active_expedition(db, profile) is not None:
        raise AppError("Only one active expedition is allowed", status_code=409)

    if target_terrain_type not in {habitat.terrain_type for habitat in profile.habitats}:
        raise AppError("This terrain is not unlocked yet", status_code=409)

    unique_ids = list(dict.fromkeys(animal_ids))
    if not 3 <= len(unique_ids) <= 5:
        raise AppError("Expedition party must contain from 3 to 5 unique animals", status_code=400)

    animals = [animal for animal in profile.animals if animal.id in unique_ids]
    if len(animals) != len(unique_ids):
        raise AppError("Some expedition animals were not found", status_code=404)
    for animal in animals:
        if animal.status != AnimalStatus.ACTIVE:
            raise AppError("Only active animals can be sent to an expedition", status_code=409)

    expedition = Expedition(
        player_season=profile,
        target_terrain_type=target_terrain_type,
        outcome=PENDING_OUTCOME,
        started_at=to_storage_datetime(now),
        resolves_at=to_storage_datetime(ensure_utc(now) + expedition_duration(target_terrain_type)),
    )
    db.add(expedition)
    db.flush()

    by_id = {animal.id: animal for animal in animals}
    for slot_order, animal_id in enumerate(unique_ids, start=1):
        animal = by_id[animal_id]
        animal.status = AnimalStatus.ON_EXPEDITION
        db.add(ExpeditionPartyMember(expedition=expedition, animal=animal, slot_order=slot_order))

    db.flush()
    return expedition


def _resolve_single_expedition(db: Session, profile: PlayerSeason, expedition: Expedition, resolved_at: datetime):
    if expedition.outcome != PENDING_OUTCOME:
        return expedition

    rng = random.Random()
    wild_animal = create_expedition_animal(profile, resolved_at, expedition.target_terrain_type, rng)
    expedition.wild_survival_gene = wild_animal.survival_gene
    expedition.wild_breeding_gene = wild_animal.breeding_gene
    expedition.wild_appearance_gene = wild_animal.appearance_gene
    expedition.wild_size_gene = wild_animal.size_gene

    living_party = [member.animal for member in expedition.party_members if member.animal.status != AnimalStatus.DEAD]
    expedition.party_power = party_combat_power(living_party)
    expedition.wild_power = animal_combat_power(wild_animal)

    if expedition.party_power >= expedition.wild_power:
        db.add(wild_animal)
        db.flush()
        expedition.captured_animal = wild_animal
        expedition.outcome = ExpeditionOutcome.SUCCESS
    else:
        if living_party:
            lost_animal = rng.choice(living_party)
            lost_animal.status = AnimalStatus.DEAD
            lost_animal.died_at = to_storage_datetime(resolved_at)
            lost_animal.current_habitat = None
            expedition.lost_animal = lost_animal
        expedition.outcome = ExpeditionOutcome.FAILURE

    for member in expedition.party_members:
        if member.animal.status == AnimalStatus.ON_EXPEDITION:
            member.animal.status = AnimalStatus.ACTIVE

    expedition.resolved_at = to_storage_datetime(resolved_at)
    db.flush()
    return expedition


def resolve_due_expeditions(db: Session, profile: PlayerSeason, expeditions: Sequence[Expedition], resolved_at: datetime):
    resolved_at_utc = ensure_utc(resolved_at)
    for expedition in expeditions:
        if expedition.outcome == PENDING_OUTCOME and ensure_utc(expedition.resolves_at) <= resolved_at_utc:
            _resolve_single_expedition(db, profile, expedition, resolved_at_utc)


def resolve_expedition(db: Session, profile: PlayerSeason, expedition_id: int, now: datetime):
    expedition = db.scalar(
        select(Expedition)
        .options(selectinload(Expedition.party_members).selectinload(ExpeditionPartyMember.animal))
        .where(Expedition.player_season_id == profile.id, Expedition.id == expedition_id)
        .limit(1)
    )
    if expedition is None:
        raise AppError("Expedition not found", status_code=404)
    if expedition.outcome != PENDING_OUTCOME:
        return expedition
    if ensure_utc(expedition.resolves_at) > ensure_utc(now):
        raise AppError("Expedition is still in progress", status_code=409)
    return _resolve_single_expedition(db, profile, expedition, ensure_utc(now))
