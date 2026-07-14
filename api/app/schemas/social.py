from __future__ import annotations

from pydantic import BaseModel, Field


class ClanCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=32)


class ClanRequestBody(BaseModel):
    clan_id: int = Field(gt=0)


class ClanSpecializationBody(BaseModel):
    specialization: str = Field(pattern="^(specialist|megapark|wild)$")


class TransferCreateBody(BaseModel):
    total_rub: int = Field(ge=1)
    max_claims: int = Field(ge=1, le=100)
