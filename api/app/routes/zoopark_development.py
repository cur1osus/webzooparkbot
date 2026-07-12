from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.schemas.development import UpgradeDevelopmentBody
from api.app.zoopark import development as development_service

router = APIRouter(tags=["development"])


@router.post("/api/development/upgrade")
def upgrade_development(body: UpgradeDevelopmentBody, tg_id: TelegramId):
    return development_service.upgrade(tg_id, body)
