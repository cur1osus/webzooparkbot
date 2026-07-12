from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class BankExchangeBody(BaseModel):
    """Rubles to dollars. There is no other direction — see `economy.py`."""

    amount_rub: int = Field(default=0, ge=0)
    exchange_all: bool = False

    @model_validator(mode="after")
    def _needs_an_amount(self) -> "BankExchangeBody":
        if not self.exchange_all and self.amount_rub <= 0:
            raise ValueError("amount_rub must be positive unless exchange_all is set")
        return self
