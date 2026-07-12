from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AdminGrantBody(BaseModel):
    currency: Literal["rub", "usd", "paw"]
    amount: int = Field(gt=0, le=1_000_000_000)


class AdminPlayerStatusBody(BaseModel):
    status: Literal["active", "banned"]
