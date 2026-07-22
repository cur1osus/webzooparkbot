from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AssignLocalityBody(BaseModel):
    animal_id: int = Field(gt=0)
    locality_id: int | None = None


class AssignMatchingLocalityBody(BaseModel):
    # Omitted means every locality the player owns. The screen always names one — it is a
    # button on a card — but a caller working from a list of what is misplaced wants the
    # whole sweep, and naming them one at a time is how localities get skipped.
    locality_id: int | None = Field(default=None, gt=0)


class ReleaseAnimalBody(BaseModel):
    animal_id: int = Field(gt=0)


class FavoriteAnimalBody(BaseModel):
    animal_id: int = Field(gt=0)
    is_favorite: bool


class BreedBody(BaseModel):
    animal_id_1: int = Field(gt=0)
    animal_id_2: int = Field(gt=0)


class OpenPackBody(BaseModel):
    # None opens the free daily gift; a tier name buys that (unlocked) tier.
    tier: str | None = None
    # Batch opening is still one user action, but each pack is charged and audited
    # independently so the season price ladder remains exact.
    quantity: Literal[1, 5, 10, 50, 100] = 1


class BuyLocalityBody(BaseModel):
    habitat: str


class UpgradeLocalityBody(BaseModel):
    locality_id: int = Field(gt=0)


class StartExpeditionBody(BaseModel):
    locality_id: int = Field(gt=0)
    animal_ids: list[int] = Field(min_length=1, max_length=16)
    # How hard a raid to take. The habitat's own cap is enforced in the domain layer, which
    # is the only place that knows it; this bound just keeps nonsense out of the model.
    depth: int = Field(default=1, ge=1, le=5)


class FinishExpeditionBody(BaseModel):
    # None resolves the oldest expedition that is ready — what a client with no id means.
    expedition_id: int | None = Field(default=None, gt=0)


class DismissExpeditionBody(BaseModel):
    expedition_id: int | None = Field(default=None, gt=0)
