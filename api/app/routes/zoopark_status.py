from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.schemas.status import CureBody
from api.app.zoopark import status as status_service

router = APIRouter(tags=["status"])


@router.get("/api/bonus")
def bonus(tg_id: TelegramId):
    return status_service.daily_bonus(tg_id)


@router.post("/api/bonus/reroll")
def bonus_reroll(tg_id: TelegramId):
    return status_service.reroll_daily_bonus(tg_id)


@router.post("/api/bonus/claim")
def bonus_claim(tg_id: TelegramId):
    return status_service.claim_bonus(tg_id)


@router.post("/api/animals/cure")
def cure_animal(body: CureBody, tg_id: TelegramId):
    return status_service.cure_animal(tg_id, body)


@router.post("/api/animals/cure-all")
def cure_all_animals(tg_id: TelegramId):
    return status_service.cure_all_animals(tg_id)
