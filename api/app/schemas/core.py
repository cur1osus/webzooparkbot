from __future__ import annotations

from pydantic import BaseModel


class SavePayload(BaseModel):
    rub: float
    usd: float
    paw_coins: float
    animals: list[dict]
    aviaries: list[dict]
    balance_seq: int
    data_version: int


class SaveResult(BaseModel):
    ok: bool
    rub: int
    usd: int
    paw_coins: int
    balance_seq: int
    data_version: int


class RegisterBody(BaseModel):
    nickname: str
