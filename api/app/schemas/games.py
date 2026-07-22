from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DonateInvoiceBody(BaseModel):
    stars: int = Field(ge=1, le=100_000)


class CocktailGuessBody(BaseModel):
    fruits: list[str] = Field(min_length=1, max_length=8)


class SafeGuessBody(BaseModel):
    code: str = Field(min_length=1, max_length=16)
