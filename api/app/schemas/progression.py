from __future__ import annotations

from pydantic import BaseModel, Field


class AssignLocalityBody(BaseModel):
    animal_id: int = Field(gt=0)
    locality_id: int | None = None


class AssignMatchingLocalityBody(BaseModel):
    locality_id: int = Field(gt=0)


class ReleaseAnimalBody(BaseModel):
    animal_id: int = Field(gt=0)


class BreedBody(BaseModel):
    animal_id_1: int = Field(gt=0)
    animal_id_2: int = Field(gt=0)


class OpenPackBody(BaseModel):
    # None opens the free daily gift; a tier name buys that (unlocked) tier.
    tier: str | None = None


class BuyLocalityBody(BaseModel):
    habitat: str


class UpgradeLocalityBody(BaseModel):
    locality_id: int = Field(gt=0)


class StartExpeditionBody(BaseModel):
    locality_id: int = Field(gt=0)
    animal_ids: list[int] = Field(min_length=1, max_length=16)
