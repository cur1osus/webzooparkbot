from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.schemas.economy import BankExchangeBody
from api.app.zoopark import economy as economy_service

router = APIRouter(tags=["economy"])


@router.get("/api/bank")
def bank(tg_id: TelegramId):
    return economy_service.bank(tg_id)


@router.post("/api/bank/exchange")
def bank_exchange(body: BankExchangeBody, tg_id: TelegramId):
    """Rubles to dollars. There is no reverse direction."""
    return economy_service.exchange(tg_id, body)
