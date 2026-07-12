from __future__ import annotations

from pydantic import BaseModel, Field


class DonateInvoiceBody(BaseModel):
    stars: int = Field(ge=1, le=100_000)


class DuelCreateBody(BaseModel):
    kind: str
    stake_rub: int = Field(ge=1)


class SoloStartBody(BaseModel):
    kind: str
    stake_rub: int = Field(ge=1)


class CocktailGuessBody(BaseModel):
    fruits: list[str] = Field(min_length=1, max_length=8)
