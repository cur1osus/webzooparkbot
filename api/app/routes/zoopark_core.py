from __future__ import annotations

from fastapi import APIRouter, Header

from api.app.core.auth import auth
from api.app.schemas.core import RegisterBody, SavePayload, SaveResult
from api.app.zoopark import core as core_service


router = APIRouter(tags=["zoopark-core"])


@router.get("/api/health")
def health():
    return core_service.health()


@router.get("/api/me")
def me(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return core_service.me(auth(x_init_data, x_dev_user_id))


@router.post("/api/save", response_model=SaveResult)
def save(
    body: SavePayload,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return core_service.save(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/register")
def register(
    body: RegisterBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return core_service.register(auth(x_init_data, x_dev_user_id), body)


@router.get("/api/config")
def config():
    return core_service.config()
