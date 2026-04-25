from __future__ import annotations

from pydantic import BaseModel


class CureBody(BaseModel):
    animal_id: str
