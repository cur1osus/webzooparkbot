from __future__ import annotations

from fastapi import APIRouter, Header

from api.app.core.auth import auth
from api.app.schemas.forge import (
    ForgeActivateBody,
    ForgeCreateBody,
    ForgeItemIdBody,
    ForgeMergeBody,
    ForgeSetBody,
    ForgeSetIdBody,
)
from api.app.zoopark.forge import (
    api_forge_activate,
    api_forge_create,
    api_forge_items,
    api_forge_merge,
    api_forge_set_apply,
    api_forge_set_create,
    api_forge_set_delete,
    api_forge_set_update,
    api_forge_sets,
    api_forge_sell,
    api_forge_upgrade,
)


router = APIRouter(tags=["zoopark-forge"])


@router.get("/api/forge/items")
def forge_items(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_items(auth(x_init_data, x_dev_user_id))


@router.get("/api/forge/sets")
def forge_sets(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_sets(auth(x_init_data, x_dev_user_id))


@router.post("/api/forge/create")
def forge_create(
    body: ForgeCreateBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_create(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/forge/sets/create")
def forge_set_create(
    body: ForgeSetBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_set_create(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/forge/sets/update")
def forge_set_update(
    body: ForgeSetBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_set_update(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/forge/sets/delete")
def forge_set_delete(
    body: ForgeSetIdBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_set_delete(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/forge/sets/apply")
def forge_set_apply(
    body: ForgeSetIdBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_set_apply(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/forge/upgrade")
def forge_upgrade(
    body: ForgeItemIdBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_upgrade(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/forge/merge")
def forge_merge(
    body: ForgeMergeBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_merge(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/forge/sell")
def forge_sell(
    body: ForgeItemIdBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_sell(auth(x_init_data, x_dev_user_id), body)


@router.post("/api/forge/activate")
def forge_activate(
    body: ForgeActivateBody,
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
):
    return api_forge_activate(auth(x_init_data, x_dev_user_id), body)
