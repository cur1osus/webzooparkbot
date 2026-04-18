from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
import random

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from api.app.core.errors import AppError
from api.app.models.animal import Animal
from api.app.models.enums import AnimalStatus
from api.app.models.expedition import Expedition, ExpeditionPartyMember
from api.app.models.habitat import PlayerHabitat
from api.app.models.player import Player
from api.app.models.player_season import PlayerSeason
from api.app.models.season import Season
from api.app.services import expedition_service
from api.app.services.logic import (
    available_locked_habitats,
    current_income_per_hour,
    ensure_utc,
    money,
    next_season_bounds,
    random_habitat,
    starting_coins,
    to_storage_datetime,
    utc_now,
)


PROFILE_LOAD_OPTIONS = (
    selectinload(PlayerSeason.player),
    selectinload(PlayerSeason.season),
    selectinload(PlayerSeason.habitats),
    selectinload(PlayerSeason.animals).selectinload(Animal.current_habitat),
)


def get_active_season(db: Session, now: datetime | None = None) -> Season:
    now = ensure_utc(now or utc_now())
    season = db.scalar(
        select(Season)
        .where(Season.starts_at <= to_storage_datetime(now), Season.ends_at > to_storage_datetime(now))
        .order_by(Season.ordinal.desc())
        .limit(1)
    )
    if season is not None:
        return season

    previous = db.scalar(select(Season).order_by(Season.ordinal.desc()).limit(1))
    ordinal, starts_at, ends_at = next_season_bounds(previous, now)
    season = Season(ordinal=ordinal, starts_at=starts_at, ends_at=ends_at)
    db.add(season)
    db.flush()
    return season


def _create_player_season(db: Session, player: Player, season: Season, now: datetime) -> PlayerSeason:
    profile = PlayerSeason(
        player=player,
        season=season,
        balance_coins=starting_coins(),
        last_income_at=to_storage_datetime(now),
    )
    db.add(profile)
    db.flush()

    granted_habitat = PlayerHabitat(
        player_season=profile,
        terrain_type=random_habitat(random.Random()),
        unlock_order=1,
        purchase_price=money("0"),
        unlocked_at=to_storage_datetime(now),
    )
    db.add(granted_habitat)
    db.flush()
    return profile


def get_player_by_telegram_id(db: Session, telegram_id: int) -> Player | None:
    return db.scalar(select(Player).where(Player.telegram_id == telegram_id).limit(1))


def ensure_player_profile(db: Session, player: Player, now: datetime | None = None) -> PlayerSeason:
    now = ensure_utc(now or utc_now())
    season = get_active_season(db, now)
    profile = db.scalar(
        select(PlayerSeason)
        .options(*PROFILE_LOAD_OPTIONS)
        .where(PlayerSeason.player_id == player.id, PlayerSeason.season_id == season.id)
        .limit(1)
    )
    if profile is None:
        profile = _create_player_season(db, player, season, now)
    return load_profile(db, player.id, season.id)


def load_profile(db: Session, player_id: int, season_id: int) -> PlayerSeason:
    profile = db.scalar(
        select(PlayerSeason)
        .options(*PROFILE_LOAD_OPTIONS)
        .where(PlayerSeason.player_id == player_id, PlayerSeason.season_id == season_id)
        .limit(1)
    )
    if profile is None:
        raise AppError("Profile for active season not found", status_code=404)
    return profile


def get_current_profile_by_telegram_id(db: Session, telegram_id: int, now: datetime | None = None) -> PlayerSeason:
    player = get_player_by_telegram_id(db, telegram_id)
    if player is None:
        raise AppError("Player is not registered", status_code=404)
    return ensure_player_profile(db, player, now)


def register_player(db: Session, telegram_id: int, nickname: str, now: datetime | None = None) -> PlayerSeason:
    now = ensure_utc(now or utc_now())
    normalized_nickname = nickname.strip()
    if len(normalized_nickname) < 3:
        raise AppError("Nickname must contain at least 3 non-space characters", status_code=422)
    existing_player = get_player_by_telegram_id(db, telegram_id)
    if existing_player is None:
        conflicting_nickname = db.scalar(
            select(Player)
            .where(func.lower(Player.nickname) == normalized_nickname.lower())
            .limit(1)
        )
        if conflicting_nickname is not None:
            raise AppError("Nickname is already taken", status_code=409)
        existing_player = Player(telegram_id=telegram_id, nickname=normalized_nickname)
        db.add(existing_player)
        db.flush()
    return ensure_player_profile(db, existing_player, now)


def pending_expeditions(db: Session, profile: PlayerSeason) -> list[Expedition]:
    return list(
        db.scalars(
            select(Expedition)
            .options(
                selectinload(Expedition.party_members).selectinload(ExpeditionPartyMember.animal)
            )
            .where(
                Expedition.player_season_id == profile.id,
                Expedition.outcome == expedition_service.PENDING_OUTCOME,
            )
            .order_by(Expedition.started_at.asc())
        )
    )


def expire_animals(profile: PlayerSeason, at: datetime) -> None:
    at_utc = ensure_utc(at)
    for animal in profile.animals:
        if animal.status == AnimalStatus.DEAD:
            continue
        if ensure_utc(animal.dies_at) <= at_utc:
            animal.status = AnimalStatus.DEAD
            animal.died_at = to_storage_datetime(at_utc)
            animal.current_habitat = None


def _next_profile_event_time(profile: PlayerSeason, active_expeditions: Sequence[Expedition], cursor: datetime, now: datetime) -> datetime:
    next_event = ensure_utc(now)
    for animal in profile.animals:
        if animal.status != AnimalStatus.DEAD:
            dies_at = ensure_utc(animal.dies_at)
            if ensure_utc(cursor) < dies_at < next_event:
                next_event = dies_at
    for expedition in active_expeditions:
        resolves_at = ensure_utc(expedition.resolves_at)
        if ensure_utc(cursor) < resolves_at < next_event:
            next_event = resolves_at
    return next_event


def sync_profile_state(db: Session, profile: PlayerSeason, now: datetime | None = None) -> PlayerSeason:
    now = ensure_utc(now or utc_now())
    active_expeditions = pending_expeditions(db, profile)

    last_income_at = ensure_utc(profile.last_income_at)
    if last_income_at >= now:
        expire_animals(profile, now)
        expedition_service.resolve_due_expeditions(db, profile, active_expeditions, now)
        profile.last_income_at = to_storage_datetime(now)
        return profile

    cursor = last_income_at
    while cursor < now:
        next_event = _next_profile_event_time(profile, active_expeditions, cursor, now)
        income_rate = current_income_per_hour(profile)
        seconds = max(0, int((next_event - cursor).total_seconds()))
        if seconds:
            profile.balance_coins = money(profile.balance_coins + (income_rate * seconds / 3600))
        cursor = next_event
        expire_animals(profile, cursor)
        expedition_service.resolve_due_expeditions(db, profile, active_expeditions, cursor)

    profile.last_income_at = to_storage_datetime(now)
    expire_animals(profile, now)
    return profile


def locked_habitats(profile: PlayerSeason):
    return available_locked_habitats(profile)
