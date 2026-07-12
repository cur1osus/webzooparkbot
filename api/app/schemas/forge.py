"""Forge request bodies.

Ids arrive as strings because the client has always sent them that way. They are coerced
to positive integers *at the boundary*, so a malformed id is a 422 from FastAPI rather
than a `ValueError` escaping the domain layer as a 500.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field


def _positive_int(value: str | int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("must be an integer id") from exc
    if parsed <= 0:
        raise ValueError("must be positive")
    return parsed


ItemId = Annotated[int, BeforeValidator(_positive_int)]


class ForgeCreateBody(BaseModel):
    currency: Annotated[str, Field(pattern="^(usd|paw)$")] = "usd"


class ForgeItemIdBody(BaseModel):
    item_id: ItemId


class ForgeActivateBody(BaseModel):
    item_id: ItemId | None = None
    # Legacy name from a client that toggled sets rather than items.
    set_id: ItemId | None = None

    def resolved_item_id(self) -> int:
        value = self.item_id if self.item_id is not None else self.set_id
        if value is None:
            raise ValueError("item_id is required")
        return value


class ForgeMergeBody(BaseModel):
    item_id1: ItemId
    item_id2: ItemId


class ForgeSetBody(BaseModel):
    set_id: ItemId | None = None
    name: str | None = Field(default=None, max_length=32)
    icon: str | None = Field(default=None, max_length=16)
    item_ids: list[ItemId] = Field(default_factory=list, max_length=16)

    def unique_item_ids(self) -> list[int]:
        seen: list[int] = []
        for item_id in self.item_ids:
            if item_id not in seen:
                seen.append(item_id)
        return seen


class ForgeSetIdBody(BaseModel):
    set_id: ItemId
