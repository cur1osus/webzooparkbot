from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.schemas.forge import (
    ForgeActivateBody,
    ForgeCreateBody,
    ForgeItemIdBody,
    ForgeMergeBody,
    ForgeSetBody,
    ForgeSetIdBody,
)
from api.app.zoopark import forge as forge_service

router = APIRouter(prefix="/api/forge", tags=["forge"])


@router.get("/items")
def items(tg_id: TelegramId):
    return forge_service.forge_items(tg_id)


@router.get("/sets")
def sets(tg_id: TelegramId):
    return forge_service.forge_sets(tg_id)


@router.post("/create")
def create(body: ForgeCreateBody, tg_id: TelegramId):
    return forge_service.forge_create(tg_id, body)


@router.post("/upgrade")
def upgrade(body: ForgeItemIdBody, tg_id: TelegramId):
    return forge_service.forge_upgrade(tg_id, body)


@router.post("/merge")
def merge(body: ForgeMergeBody, tg_id: TelegramId):
    return forge_service.forge_merge(tg_id, body)


@router.post("/sell")
def sell(body: ForgeItemIdBody, tg_id: TelegramId):
    return forge_service.forge_sell(tg_id, body)


@router.post("/activate")
def activate(body: ForgeActivateBody, tg_id: TelegramId):
    return forge_service.forge_activate(tg_id, body)


@router.post("/sets/create")
def set_create(body: ForgeSetBody, tg_id: TelegramId):
    return forge_service.forge_set_create(tg_id, body)


@router.post("/sets/update")
def set_update(body: ForgeSetBody, tg_id: TelegramId):
    return forge_service.forge_set_update(tg_id, body)


@router.post("/sets/delete")
def set_delete(body: ForgeSetIdBody, tg_id: TelegramId):
    return forge_service.forge_set_delete(tg_id, body)


@router.post("/sets/apply")
def set_apply(body: ForgeSetIdBody, tg_id: TelegramId):
    return forge_service.forge_set_apply(tg_id, body)
