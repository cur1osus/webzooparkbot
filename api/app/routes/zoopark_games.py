from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.schemas.games import CocktailGuessBody, DonateInvoiceBody, DuelCreateBody, SafeGuessBody, SoloStartBody
from api.app.zoopark import games as games_service
from api.app.zoopark import safe as safe_service

router = APIRouter(tags=["games"])


@router.get("/api/duels")
def open_duels(tg_id: TelegramId):
    return games_service.open_duels(tg_id)


@router.post("/api/duels")
def create_duel(body: DuelCreateBody, tg_id: TelegramId):
    return games_service.create_duel(tg_id, body)


@router.get("/api/duels/{duel_id}")
def get_duel(duel_id: int, tg_id: TelegramId):
    return games_service.get_duel(duel_id, tg_id)


@router.post("/api/duels/{duel_id}/join")
def join_duel(duel_id: int, tg_id: TelegramId):
    return games_service.join_duel(tg_id, duel_id)


@router.post("/api/duels/{duel_id}/resolve")
def resolve_duel(duel_id: int, tg_id: TelegramId):
    return games_service.resolve_duel(tg_id, duel_id)


@router.post("/api/duels/{duel_id}/cancel")
def cancel_duel(duel_id: int, tg_id: TelegramId):
    return games_service.cancel_duel(tg_id, duel_id)


@router.post("/api/solo")
def start_solo_game(body: SoloStartBody, tg_id: TelegramId):
    return games_service.start_solo_game(tg_id, body)


@router.get("/api/solo/current")
def current_solo_game(tg_id: TelegramId):
    return games_service.current_solo_game(tg_id)


@router.post("/api/solo/finish")
def finish_solo_game(tg_id: TelegramId):
    return games_service.finish_solo_game(tg_id)


@router.get("/api/solo/stats")
def solo_stats(tg_id: TelegramId):
    return games_service.solo_stats(tg_id)


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
