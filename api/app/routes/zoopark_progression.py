from __future__ import annotations

from fastapi import APIRouter, Header

from api.app.core.auth import auth
from api.app.schemas.progression import AssignLocalityBody, BreedBody, BuyLocalityBody, StartExpeditionBody
from api.app.zoopark.progression import api_assign_locality, api_breed, api_buy_locality, api_dismiss_expedition, api_finish_expedition, api_get_expeditions, api_get_localities, api_packs_info, api_packs_open, api_start_expedition


router = APIRouter(tags=["zoopark-progression"])


@router.get("/api/packs/info")
def packs_info(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_packs_info(auth(x_init_data, x_dev_user_id))


@router.post("/api/packs/open")
def packs_open(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_packs_open(auth(x_init_data, x_dev_user_id))


@router.get("/api/localities")
def get_localities(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_get_localities(auth(x_init_data, x_dev_user_id))


@router.post("/api/localities/buy")
def buy_locality(
    body: BuyLocalityBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_buy_locality(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/localities/assign")
def assign_locality(
    body: AssignLocalityBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_assign_locality(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/breed")
def breed(
    body: BreedBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_breed(auth(x_init_data, x_dev_user_id), body)


@router.get("/api/expeditions")
def get_expeditions(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_get_expeditions(auth(x_init_data, x_dev_user_id))


@router.post("/api/expeditions/start")
def start_expedition(
    body: StartExpeditionBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_start_expedition(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/expeditions/finish")
def finish_expedition(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_finish_expedition(auth(x_init_data, x_dev_user_id))


@router.post("/api/expeditions/dismiss")
def dismiss_expedition(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_dismiss_expedition(auth(x_init_data, x_dev_user_id))
