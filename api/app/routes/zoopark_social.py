from __future__ import annotations

from fastapi import APIRouter, Header

from api.app.core.auth import auth
from api.app.schemas.social import ClanCreateBody, ClanRequestBody, TransferCreateBody
from api.app.zoopark.social import api_clan_create, api_clan_leave, api_clan_list, api_clan_members, api_clan_request, api_my_transfers, api_referrals, api_top, api_transfers_create


router = APIRouter(tags=["zoopark-social"])


@router.get("/api/top")
def top_page(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_top(auth(x_init_data, x_dev_user_id))


@router.get("/api/clan/list")
def clan_list(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_clan_list(auth(x_init_data, x_dev_user_id))


@router.post("/api/clan/create")
def clan_create(
    body: ClanCreateBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_clan_create(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/clan/request")
def clan_request(
    body: ClanRequestBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_clan_request(auth(x_init_data, x_dev_user_id), body)


@router.get("/api/clan/members")
def clan_members(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_clan_members(auth(x_init_data, x_dev_user_id))


@router.post("/api/clan/leave")
def clan_leave(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_clan_leave(auth(x_init_data, x_dev_user_id))


@router.get("/api/referrals")
def referrals(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_referrals(auth(x_init_data, x_dev_user_id))


@router.post("/api/transfers/create")
def transfers_create(
    body: TransferCreateBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_transfers_create(auth(x_init_data, x_dev_user_id), body)


@router.get("/api/my-transfers")
def my_transfers(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_my_transfers(auth(x_init_data, x_dev_user_id))
