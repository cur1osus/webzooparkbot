from __future__ import annotations

from pydantic import BaseModel


class DonateInvoiceBody(BaseModel):
    stars: int


class MpCreateBody(BaseModel):
    game_type: str
    bet_rub: float


class SoloStartBody(BaseModel):
    game_type: str
    bet_rub: float
