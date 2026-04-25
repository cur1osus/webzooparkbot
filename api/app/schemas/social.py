from __future__ import annotations

from pydantic import BaseModel


class ClanCreateBody(BaseModel):
    name: str
    spec: str | None = None


class ClanRequestBody(BaseModel):
    clan_id: int


class TransferCreateBody(BaseModel):
    total_rub: float
    max_claims: int
