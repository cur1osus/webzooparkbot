from __future__ import annotations

from fastapi import APIRouter, Header

from api.app.zoopark.merchant import buy_merchant_offer, get_merchant_animals
from api.app.zoopark.runtime import auth


router = APIRouter(tags=["zoopark-merchant"])


@router.get("/api/merchant/animals")
def merchant_animals(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return get_merchant_animals(auth(x_init_data, x_dev_user_id))


@router.post("/api/merchant/buy1")
def merchant_buy1(x_init_data: str = Header(default=""), x_dev_user_id: str = Header(default="")):
    return buy_merchant_offer(auth(x_init_data, x_dev_user_id), 1)


@router.post("/api/merchant/buy2")
def merchant_buy2(x_init_data: str = Header(default=""), x_dev_user_id: str = Header(default="")):
    return buy_merchant_offer(auth(x_init_data, x_dev_user_id), 2)


@router.post("/api/merchant/buy3")
def merchant_buy3(x_init_data: str = Header(default=""), x_dev_user_id: str = Header(default="")):
    return buy_merchant_offer(auth(x_init_data, x_dev_user_id), 3)
