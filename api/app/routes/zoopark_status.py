from __future__ import annotations

from fastapi import APIRouter, Header

from api.app.core.auth import auth
from api.app.schemas.status import CureBody
from api.app.zoopark import status as status_service


router = APIRouter(tags=["zoopark-status"])


@router.post("/api/claim_bonus")
def claim_bonus(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return status_service.claim_bonus(auth(x_init_data, x_dev_user_id))


@router.post("/api/cure_animal")
def cure_animal(
    body: CureBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return status_service.cure_animal(auth(x_init_data, x_dev_user_id), body)
