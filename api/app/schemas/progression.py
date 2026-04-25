from __future__ import annotations

from pydantic import BaseModel


class AssignLocalityBody(BaseModel):
    animal_id: int
    locality_id: int | None


class BreedBody(BaseModel):
    animal_id_1: int
    animal_id_2: int


class BuyLocalityBody(BaseModel):
    habitat: str


class StartExpeditionBody(BaseModel):
    locality_id: int
    animal_ids: list[int]
