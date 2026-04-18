from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.app.core.auth import require_telegram_id
from api.app.db.session import get_db_session
import api.app.models  # noqa: F401 — ensure all ORM models are registered before mapper configuration
from api.app.domain.balance import BASE_ANIMAL_INCOME_PER_HOUR, BASE_HABITAT_UNLOCK_PRICE, BASE_PACK_PRICE, PACK_PRICE_GROWTH, SEASON_LENGTH_DAYS, STARTING_COINS
from api.app.schemas.game import (
    AnimalAssignmentResponse,
    AssignAnimalHabitatRequest,
    BreedAnimalsRequest,
    BreedAnimalsResponse,
    ConfigResponse,
    ExpeditionResolveResponse,
    ExpeditionStartResponse,
    HealthResponse,
    HabitatUnlockResponse,
    PackOpenResponse,
    ProfileResponse,
    RegisterRequest,
    StartExpeditionRequest,
    UnlockHabitatRequest,
)
from api.app.services import breeding_service, expedition_service, habitat_service, pack_service, profile_service
from api.app.services.logic import utc_now
from api.app.services.serializers import build_profile_response, serialize_animal, serialize_breeding_attempt, serialize_expedition, serialize_habitat, serialize_pack_opening


router = APIRouter(prefix="/api", tags=["game"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(ok=True)


@router.get("/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    return ConfigResponse(
        season_length_days=SEASON_LENGTH_DAYS,
        base_pack_price=format(BASE_PACK_PRICE, "f"),
        pack_price_growth=str(PACK_PRICE_GROWTH),
        base_habitat_unlock_price=format(BASE_HABITAT_UNLOCK_PRICE, "f"),
        starting_coins=format(STARTING_COINS, "f"),
        base_animal_income_per_hour=format(BASE_ANIMAL_INCOME_PER_HOUR, "f"),
    )


@router.post("/register", response_model=ProfileResponse)
def register(
    body: RegisterRequest,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> ProfileResponse:
    now = utc_now()
    profile = profile_service.register_player(db, telegram_id, body.nickname, now)
    profile_service.sync_profile_state(db, profile, now)
    db.commit()
    profile = profile_service.ensure_player_profile(db, profile.player, now)
    return build_profile_response(db, profile, now)


@router.get("/me", response_model=ProfileResponse)
def me(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> ProfileResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    db.commit()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    return build_profile_response(db, profile, now)


@router.post("/packs/open", response_model=PackOpenResponse)
def open_pack(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> PackOpenResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    opening = pack_service.open_pack(db, profile, now)
    db.commit()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    return PackOpenResponse(opening=serialize_pack_opening(opening, now), profile=build_profile_response(db, profile, now))


@router.post("/habitats/unlock", response_model=HabitatUnlockResponse)
def unlock_habitat(
    body: UnlockHabitatRequest,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> HabitatUnlockResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    habitat = habitat_service.unlock_habitat(db, profile, body.terrain_type, now)
    db.commit()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    return HabitatUnlockResponse(habitat=serialize_habitat(profile, habitat), profile=build_profile_response(db, profile, now))


@router.post("/animals/{animal_id}/assign-habitat", response_model=AnimalAssignmentResponse)
def assign_habitat(
    animal_id: str,
    body: AssignAnimalHabitatRequest,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> AnimalAssignmentResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    animal = habitat_service.assign_animal_to_habitat(profile, animal_id, body.habitat_id)
    db.commit()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    return AnimalAssignmentResponse(animal=serialize_animal(animal, now), profile=build_profile_response(db, profile, now))


@router.post("/breeding/attempt", response_model=BreedAnimalsResponse)
def breed_animals(
    body: BreedAnimalsRequest,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> BreedAnimalsResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    attempt = breeding_service.breed_animals(db, profile, body.first_parent_id, body.second_parent_id, now)
    db.commit()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    return BreedAnimalsResponse(attempt=serialize_breeding_attempt(attempt), profile=build_profile_response(db, profile, now))


@router.post("/expeditions", response_model=ExpeditionStartResponse)
def start_expedition(
    body: StartExpeditionRequest,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> ExpeditionStartResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    expedition = expedition_service.start_expedition(db, profile, body.target_terrain_type, body.animal_ids, now)
    db.commit()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    return ExpeditionStartResponse(expedition=serialize_expedition(expedition), profile=build_profile_response(db, profile, now))


@router.post("/expeditions/{expedition_id}/resolve", response_model=ExpeditionResolveResponse)
def resolve_expedition(
    expedition_id: int,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> ExpeditionResolveResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    expedition = expedition_service.resolve_expedition(db, profile, expedition_id, now)
    db.commit()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    return ExpeditionResolveResponse(expedition=serialize_expedition(expedition), profile=build_profile_response(db, profile, now))
