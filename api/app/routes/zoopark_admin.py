from __future__ import annotations

from fastapi import APIRouter, Query

from api.app.routes._auth import TelegramId
from api.app.schemas.admin import AdminGrantBody, AdminPlayerStatusBody
from api.app.zoopark import admin as admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview")
def admin_overview(tg_id: TelegramId, search: str = Query(default="", max_length=64)):
    return admin_service.overview(tg_id, search)


@router.post("/players/{telegram_id}/grant")
def admin_grant(telegram_id: int, body: AdminGrantBody, tg_id: TelegramId):
    return admin_service.grant_currency(tg_id, telegram_id, body)


@router.post("/players/{telegram_id}/status")
def admin_status(telegram_id: int, body: AdminPlayerStatusBody, tg_id: TelegramId):
    return admin_service.set_player_status(tg_id, telegram_id, body.status)
