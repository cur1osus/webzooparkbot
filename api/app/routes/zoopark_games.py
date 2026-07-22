from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.schemas.games import CocktailGuessBody, DonateInvoiceBody, SafeGuessBody
from api.app.zoopark import games as games_service
from api.app.zoopark import safe as safe_service

router = APIRouter(tags=["games"])


@router.get("/api/safe")
def safe_state(tg_id: TelegramId):
    return safe_service.safe_state(tg_id)


@router.post("/api/safe/guess")
def safe_guess(body: SafeGuessBody, tg_id: TelegramId):
    return safe_service.safe_guess(tg_id, body)


@router.get("/api/donate/info")
def donate_info(tg_id: TelegramId):
    return games_service.donate_info()


@router.post("/api/donate/invoice")
def donate_invoice(body: DonateInvoiceBody, tg_id: TelegramId):
    return games_service.donate_invoice(tg_id, body)


@router.post("/api/cocktail/guess")
def cocktail_guess(body: CocktailGuessBody, tg_id: TelegramId):
    return games_service.cocktail_guess(tg_id, body)


@router.get("/api/cocktail")
def cocktail_state(tg_id: TelegramId):
    return games_service.cocktail_state(tg_id)
