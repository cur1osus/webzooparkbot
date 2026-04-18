from __future__ import annotations

from datetime import datetime
import random

from sqlalchemy.orm import Session

from api.app.core.errors import AppError
from api.app.models.breeding import BreedingAttempt
from api.app.models.enums import AnimalStatus
from api.app.models.player_season import PlayerSeason
from api.app.services.logic import breeding_success_probability, create_bred_animal, current_season_day


def breed_animals(db: Session, profile: PlayerSeason, first_parent_id: str, second_parent_id: str, now: datetime):
    if first_parent_id == second_parent_id:
        raise AppError("Breeding requires two different parent animals", status_code=400)

    first_parent = next((animal for animal in profile.animals if animal.id == first_parent_id), None)
    second_parent = next((animal for animal in profile.animals if animal.id == second_parent_id), None)
    if first_parent is None or second_parent is None:
        raise AppError("Both parent animals must exist", status_code=404)

    for animal in (first_parent, second_parent):
        if animal.status != AnimalStatus.ACTIVE:
            raise AppError("Only active animals can be used for breeding", status_code=409)

    season_day = current_season_day(profile.season, now)
    for animal in (first_parent, second_parent):
        if animal.last_breeding_day == season_day:
            raise AppError("Each animal can breed only once per season day", status_code=409)

    probability = breeding_success_probability(first_parent.breeding_gene, second_parent.breeding_gene)
    success = random.Random().random() < float(probability)
    child = None
    if success:
        child = create_bred_animal(profile, now, first_parent, second_parent, random.Random())
        db.add(child)
        db.flush()

    first_parent.last_breeding_day = season_day
    second_parent.last_breeding_day = season_day

    attempt = BreedingAttempt(
        player_season=profile,
        season_day=season_day,
        first_parent=first_parent,
        second_parent=second_parent,
        success_probability=probability,
        was_successful=success,
        child_animal=child,
    )
    db.add(attempt)
    db.flush()
    return attempt
