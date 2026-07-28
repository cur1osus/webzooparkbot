from __future__ import annotations

from fastapi import APIRouter, Query

from api.app.routes._auth import TelegramId
from api.app.schemas.progression import AssignLocalityBody, AssignMatchingLocalityBody, BreedBody, BuyLocalityBody, DismissExpeditionBody, FavoriteAnimalBody, FinishExpeditionBody, OpenPackBody, ReleaseAnimalBody, ReleaseAnimalsBody, StartExpeditionBody, UpgradeLocalityBody
from api.app.zoopark import progression as progression_service

router = APIRouter(tags=["progression"])


@router.get("/api/animals")
def list_animals(tg_id: TelegramId):
    return progression_service.list_available_animals(tg_id)


@router.get("/api/zoo/animals")
def list_zoo_animals(
    tg_id: TelegramId,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=120, ge=1, le=240),
    sort: str = Query(default="new"),
):
    return progression_service.list_zoo_animals(tg_id, offset=offset, limit=limit, sort=sort)


@router.get("/api/zoo/forecast")
def animal_forecast(tg_id: TelegramId):
    return progression_service.animal_forecast(tg_id)


@router.get("/api/animals/{animal_id}")
def get_animal(animal_id: int, tg_id: TelegramId):
    return progression_service.get_animal(tg_id, animal_id)


@router.get("/api/breeding/animals")
def list_breeding_animals(tg_id: TelegramId):
    return progression_service.list_breeding_animals(tg_id)


@router.get("/api/breeding/animals/page")
def list_breeding_animals_page(
    tg_id: TelegramId,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=120, ge=1, le=240),
    sort: str = Query(default="new"),
    query: str = Query(default="", max_length=64),
    species_code: str | None = Query(default=None),
    exclude_id: int | None = Query(default=None, gt=0),
):
    return progression_service.list_breeding_animals_page(
        tg_id, offset=offset, limit=limit, sort=sort, query=query,
        species_code=species_code, exclude_id=exclude_id,
    )


@router.get("/api/packs/info")
def packs_info(tg_id: TelegramId):
    return progression_service.packs_info(tg_id)


@router.post("/api/packs/open")
def open_pack(tg_id: TelegramId, body: OpenPackBody = OpenPackBody()):
    return progression_service.open_pack(tg_id, body.tier, body.quantity)


@router.get("/api/localities")
def list_localities(tg_id: TelegramId):
    return progression_service.list_localities(tg_id)


@router.get("/api/localities/summary")
def list_localities_summary(tg_id: TelegramId):
    return progression_service.list_localities_summary(tg_id)


@router.get("/api/localities/animals/page")
def list_locality_animals_page(
    tg_id: TelegramId,
    locality_id: int | None = Query(default=None, gt=0),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=120, ge=1, le=240),
    query: str = Query(default="", max_length=64),
    preferred_habitat: str | None = Query(default=None),
):
    return progression_service.list_locality_animals_page(
        tg_id,
        locality_id=locality_id,
        offset=offset,
        limit=limit,
        query=query,
        preferred_habitat=preferred_habitat,
    )


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


@router.post("/api/animals/release-batch")
def release_animals(body: ReleaseAnimalsBody, tg_id: TelegramId):
    return progression_service.release_animals(tg_id, body)


@router.post("/api/animals/favorite")
def favorite_animal(body: FavoriteAnimalBody, tg_id: TelegramId):
    return progression_service.favorite_animal(tg_id, body)


@router.post("/api/breed")
def breed(body: BreedBody, tg_id: TelegramId):
    return progression_service.breed(tg_id, body)


@router.get("/api/expeditions")
def get_expeditions(tg_id: TelegramId):
    return progression_service.get_expeditions(tg_id)


@router.get("/api/expeditions/animals/page")
def list_expedition_animals_page(
    tg_id: TelegramId,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=120, ge=1, le=240),
    query: str = Query(default="", max_length=64),
):
    return progression_service.list_expedition_animals_page(tg_id, offset=offset, limit=limit, query=query)


@router.post("/api/expeditions/start")
def start_expedition(body: StartExpeditionBody, tg_id: TelegramId):
    return progression_service.start_expedition(tg_id, body)


@router.post("/api/expeditions/finish")
def finish_expedition(tg_id: TelegramId, body: FinishExpeditionBody = FinishExpeditionBody()):
    return progression_service.finish_expedition(tg_id, body.expedition_id)


@router.post("/api/expeditions/dismiss")
def dismiss_expedition(tg_id: TelegramId, body: DismissExpeditionBody = DismissExpeditionBody()):
    return progression_service.dismiss_expedition(tg_id, body.expedition_id)
