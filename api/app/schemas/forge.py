from __future__ import annotations

from pydantic import BaseModel



class ForgeCreateBody(BaseModel):
    currency: str = "usd"  # "usd" | "paw"


class ForgeItemIdBody(BaseModel):
    item_id: str


class ForgeActivateBody(BaseModel):
    set_id: str


class ForgeSetBody(BaseModel):
    set_id: str | None = None
    name: str | None = None
    icon: str | None = None
    item_ids: list[str] = []


class ForgeSetIdBody(BaseModel):
    set_id: str


class ForgeMergeBody(BaseModel):
    item_id1: str
    item_id2: str
