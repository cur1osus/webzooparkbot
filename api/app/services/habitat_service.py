from __future__ import annotations

from sqlalchemy.orm import Session

from api.app.core.errors import AppError
from api.app.models.habitat import PlayerHabitat
from api.app.models.player_season import PlayerSeason
from api.app.models.enums import AnimalStatus, HabitatType
from api.app.services.logic import habitat_unlock_price, to_storage_datetime


def unlock_habitat(db: Session, profile: PlayerSeason, terrain_type: HabitatType, now):
    existing = next((habitat for habitat in profile.habitats if habitat.terrain_type == terrain_type), None)
    if existing is not None:
        raise AppError("Habitat already unlocked", status_code=409)
    if len(profile.habitats) >= len(HabitatType):
        raise AppError("All habitats are already unlocked", status_code=409)

    price = habitat_unlock_price(len(profile.habitats))
    if profile.balance_coins < price:
        raise AppError("Not enough coins to unlock this habitat", status_code=409)

    profile.balance_coins -= price
    habitat = PlayerHabitat(
        player_season=profile,
        terrain_type=terrain_type,
        unlock_order=len(profile.habitats) + 1,
        purchase_price=price,
        unlocked_at=to_storage_datetime(now),
    )
    db.add(habitat)
    db.flush()
    return habitat


def assign_animal_to_habitat(profile: PlayerSeason, animal_id: str, habitat_id: int):
    animal = next((candidate for candidate in profile.animals if candidate.id == animal_id), None)
    if animal is None:
        raise AppError("Animal not found", status_code=404)
    if animal.status != AnimalStatus.ACTIVE:
        raise AppError("Only active animals can be assigned to habitats", status_code=409)

    habitat = next((candidate for candidate in profile.habitats if candidate.id == habitat_id), None)
    if habitat is None:
        raise AppError("Habitat not found", status_code=404)

    animal.current_habitat = habitat
    return animal
