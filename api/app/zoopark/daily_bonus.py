"""Shared daily-bonus rolling logic used by the API and notification worker."""

from __future__ import annotations

from random import SystemRandom

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db.models import Locality, Player
from api.app.zoopark.catalog import (
    BONUS_KIND_WEIGHTS,
    BONUS_REWARD_VALUES,
    BONUS_REWARD_WEIGHTS,
    HABITATS,
    SPECIES_BY_ID,
    SPECIES_IDS_BY_RARITY,
    SPECIES_RARITY_WEIGHTS,
)
from api.app.zoopark.season import ensure_player_season

random = SystemRandom()


def _available_locality_habitats(session: Session, player: Player) -> list[str]:
    season = ensure_player_season(session, player)
    taken = set(session.scalars(
        select(Locality.habitat).where(
            Locality.player_id == player.id,
            Locality.season_id == season.id,
        )
    ).all())
    return [habitat for habitat in HABITATS if habitat not in taken]


def _roll_species_code() -> str:
    rarity = random.choices(
        list(SPECIES_RARITY_WEIGHTS),
        weights=list(SPECIES_RARITY_WEIGHTS.values()),
    )[0]
    species_id = random.choice(SPECIES_IDS_BY_RARITY[rarity])
    return SPECIES_BY_ID[species_id]["code"]


def roll_daily_bonus_offer(session: Session, player: Player) -> tuple[str, int, str | None]:
    """Return (kind, amount, reward_code) for one durable daily offer.

    Localities and animals are deliberately only 4% each. A locality is removed from
    the roll when the player already owns all five habitats.
    """
    available_localities = _available_locality_habitats(session, player)
    kinds = dict(BONUS_KIND_WEIGHTS)
    if not available_localities:
        kinds.pop("locality", None)
    kind = random.choices(list(kinds), weights=list(kinds.values()))[0]

    if kind == "animal":
        return kind, 1, _roll_species_code()
    if kind == "locality":
        return kind, 1, random.choice(available_localities)

    amount = random.choices(
        BONUS_REWARD_VALUES[kind],
        weights=BONUS_REWARD_WEIGHTS[kind],
    )[0]
    return kind, amount, None
