from __future__ import annotations

from pydantic import BaseModel, Field


class BuyAnimalBody(BaseModel):
    animal_id: str
    quantity: int = 1


class BuyAviaryBody(BaseModel):
    aviary_id: str


class BankExchangeBody(BaseModel):
    from_: str = Field(alias="from")
    amount: float = 0
    exchange_all: bool = False
