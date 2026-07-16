from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AdminGrantBody(BaseModel):
    currency: Literal["rub", "usd", "paw"]
    amount: int = Field(gt=0, le=1_000_000_000)


class AdminPlayerStatusBody(BaseModel):
    status: Literal["active", "banned"]


class AdminMaintenanceBody(BaseModel):
    duration_minutes: int = Field(ge=1, le=1_440)
    message: str = Field(default="Технический перерыв", max_length=160)


class AdminCreateAchievementBody(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=180)
    audience: Literal["all", "selected"]
    player_tg_ids: list[int] = Field(default_factory=list, max_length=500)
    image_data: str = Field(min_length=20, max_length=2_500_000)
