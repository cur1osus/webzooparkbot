from __future__ import annotations

from pydantic import BaseModel, Field


class CureBody(BaseModel):
    animal_id: int = Field(gt=0)
