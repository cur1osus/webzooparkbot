from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.zoopark import subscriptions

router = APIRouter(tags=["subscriptions"])


@router.post("/api/social/subscriptions/sync")
def sync_social_subscriptions(tg_id: TelegramId):
    return subscriptions.sync_player(tg_id)
