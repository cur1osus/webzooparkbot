from __future__ import annotations

from fastapi import APIRouter, Header, Request

from api.app.zoopark.games import DonateInvoiceBody, MpCreateBody, SoloStartBody, api_cocktail_guess, api_donate_info, api_donate_invoice, api_get_solo_stats, api_mpgame_create, api_mpgame_join, api_mpgame_open, api_mpgame_throw, api_start_solo_game
from api.app.zoopark.runtime import auth


router = APIRouter(tags=["zoopark-games"])


@router.get("/api/mpgame/open")
def mpgame_open(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    auth(x_init_data, x_dev_user_id)
    return api_mpgame_open()


@router.post("/api/mpgame/create")
def mpgame_create(
    body: MpCreateBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_mpgame_create(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/mpgame/{game_id}/join")
def mpgame_join(
    game_id: int,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_mpgame_join(auth(x_init_data, x_dev_user_id), game_id)


@router.post("/api/mpgame/{game_id}/throw")
def mpgame_throw(
    game_id: int,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    auth(x_init_data, x_dev_user_id)
    return api_mpgame_throw(game_id)


@router.post("/api/start_solo_game")
def start_solo_game(
    body: SoloStartBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_start_solo_game(auth(x_init_data, x_dev_user_id), body)


@router.get("/api/get_solo_stats")
def get_solo_stats(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_get_solo_stats(auth(x_init_data, x_dev_user_id))


@router.get("/api/donate/info")
def donate_info(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    auth(x_init_data, x_dev_user_id)
    return api_donate_info()


@router.post("/api/donate/invoice")
def donate_invoice(
    body: DonateInvoiceBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_donate_invoice(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/cocktail/guess")
async def cocktail_guess(
    request: Request,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    payload = await request.json()
    return api_cocktail_guess(auth(x_init_data, x_dev_user_id), payload.get("fruits", []))
