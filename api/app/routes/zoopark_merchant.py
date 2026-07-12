from __future__ import annotations

from fastapi import APIRouter, Path

from api.app.routes._auth import TelegramId
from api.app.zoopark import merchant as merchant_service

router = APIRouter(tags=["merchant"])


@router.get("/api/merchant/animals")
def merchant_animals(tg_id: TelegramId):
    return merchant_service.merchant_animals(tg_id)


@router.post("/api/merchant/buy/{slot}")
def merchant_buy(tg_id: TelegramId, slot: int = Path(ge=1, le=3)):
    """One route with a slot, not `buy1` / `buy2` / `buy3`."""
    return merchant_service.buy_offer(tg_id, slot)
