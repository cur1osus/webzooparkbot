from __future__ import annotations

from fastapi import APIRouter, Header

from api.app.core.auth import auth
from api.app.schemas.economy import BankExchangeBody, BuyAnimalBody, BuyAviaryBody
from api.app.zoopark import economy as economy_service


router = APIRouter(tags=["zoopark-economy"])


@router.post("/api/buy_animal")
def buy_animal(
    body: BuyAnimalBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return economy_service.buy_animal(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/buy_aviary")
def buy_aviary(
    body: BuyAviaryBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return economy_service.buy_aviary(auth(x_init_data, x_dev_user_id), body)


@router.get("/api/bank")
def bank(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    auth(x_init_data, x_dev_user_id)
    return economy_service.bank()


@router.post("/api/bank/exchange")
def bank_exchange(
    body: BankExchangeBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return economy_service.bank_exchange(auth(x_init_data, x_dev_user_id), body)
