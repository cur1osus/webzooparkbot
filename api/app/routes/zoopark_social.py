from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.schemas.social import ClanCreateBody, ClanRequestBody, TransferCreateBody
from api.app.zoopark import social as social_service

router = APIRouter(tags=["social"])


@router.get("/api/top")
def top(tg_id: TelegramId):
    return social_service.top(tg_id)


@router.get("/api/clans")
def clan_list(tg_id: TelegramId):
    return social_service.clan_list(tg_id)


@router.post("/api/clans")
def clan_create(body: ClanCreateBody, tg_id: TelegramId):
    return social_service.clan_create(tg_id, body)


@router.post("/api/clans/join")
def clan_join(body: ClanRequestBody, tg_id: TelegramId):
    return social_service.clan_join(tg_id, body)


@router.get("/api/clans/members")
def clan_members(tg_id: TelegramId):
    return social_service.clan_members(tg_id)


@router.post("/api/clans/leave")
def clan_leave(tg_id: TelegramId):
    return social_service.clan_leave(tg_id)


@router.get("/api/referrals")
def referrals(tg_id: TelegramId):
    return social_service.referrals(tg_id)


@router.post("/api/transfers")
def transfers_create(body: TransferCreateBody, tg_id: TelegramId):
    return social_service.transfers_create(tg_id, body)


@router.get("/api/transfers")
def my_transfers(tg_id: TelegramId):
    return social_service.my_transfers(tg_id)


@router.post("/api/transfers/{code}/claim")
def transfer_claim(code: str, tg_id: TelegramId):
    return social_service.transfer_claim(tg_id, code)
