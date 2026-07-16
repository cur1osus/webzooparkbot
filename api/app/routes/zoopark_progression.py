from __future__ import annotations

from fastapi import APIRouter

from api.app.routes._auth import TelegramId
from api.app.schemas.progression import AssignLocalityBody, AssignMatchingLocalityBody, BreedBody, BuyLocalityBody, DismissExpeditionBody, FinishExpeditionBody, OpenPackBody, ReleaseAnimalBody, StartExpeditionBody, UpgradeLocalityBody
from api.app.zoopark import progression as progression_service

router = APIRouter(tags=["progression"])


@router.get("/api/animals")
def list_animals(tg_id: TelegramId):
    return progression_service.list_available_animals(tg_id)


@router.get("/api/packs/info")
def packs_info(tg_id: TelegramId):
    return progression_service.packs_info(tg_id)


@router.post("/api/packs/open")
def open_pack(tg_id: TelegramId, body: OpenPackBody = OpenPackBody()):
    return progression_service.open_pack(tg_id, body.tier)


@router.get("/api/localities")
def list_localities(tg_id: TelegramId):
    return progression_service.list_localities(tg_id)


@router.post("/api/localities/buy")
def buy_locality(body: BuyLocalityBody, tg_id: TelegramId):
    return progression_service.buy_locality(tg_id, body)


@router.post("/api/localities/upgrade")
def upgrade_locality(body: UpgradeLocalityBody, tg_id: TelegramId):
    return progression_service.upgrade_locality(tg_id, body)


@router.post("/api/localities/assign")
def assign_locality(body: AssignLocalityBody, tg_id: TelegramId):
    return progression_service.assign_locality(tg_id, body)


@router.post("/api/localities/assign-matching")
def assign_matching_locality(body: AssignMatchingLocalityBody, tg_id: TelegramId):
    return progression_service.assign_matching_locality(tg_id, body)


@router.post("/api/animals/release")
def release_animal(body: ReleaseAnimalBody, tg_id: TelegramId):
    return progression_service.release_animal(tg_id, body)


@router.post("/api/breed")
def breed(body: BreedBody, tg_id: TelegramId):
    return progression_service.breed(tg_id, body)


@router.get("/api/expeditions")
def get_expeditions(tg_id: TelegramId):
    return progression_service.get_expeditions(tg_id)


@router.post("/api/expeditions/start")
def start_expedition(body: StartExpeditionBody, tg_id: TelegramId):
    return progression_service.start_expedition(tg_id, body)


@router.post("/api/expeditions/finish")
def finish_expedition(tg_id: TelegramId, body: FinishExpeditionBody = FinishExpeditionBody()):
    return progression_service.finish_expedition(tg_id, body.expedition_id)


@router.post("/api/expeditions/dismiss")
def dismiss_expedition(tg_id: TelegramId, body: DismissExpeditionBody = DismissExpeditionBody()):
    return progression_service.dismiss_expedition(tg_id, body.expedition_id)
