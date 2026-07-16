from __future__ import annotations

from fastapi import APIRouter, Response

from api.app.routes._auth import TelegramId
from api.app.schemas.core import (
    NicknameColorBody,
    ProfileAvatarBody,
    ProfileFrameBody,
    ProfileWallpaperBody,
    RegisterBody,
)
from api.app.zoopark import core as core_service
from api.app.zoopark import admin as admin_service

router = APIRouter(tags=["core"])


@router.get("/api/health")
def health():
    return core_service.health()


@router.get("/api/config")
def config(tg_id: TelegramId):
    del tg_id
    return core_service.config()


@router.get("/api/me")
def me(tg_id: TelegramId):
    return core_service.me(tg_id)


@router.get("/api/achievements/{achievement_id}/image")
def achievement_image(achievement_id: str):
    image_data, image_mime = admin_service.custom_achievement_image(achievement_id)
    return Response(content=image_data, media_type=image_mime, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/api/maintenance")
def maintenance_status(tg_id: TelegramId):
    return core_service.maintenance_status(tg_id)


@router.post("/api/profile/nickname-color")
def set_nickname_color(body: NicknameColorBody, tg_id: TelegramId):
    return core_service.set_nickname_color(tg_id, body)


@router.post("/api/profile/avatar")
def set_profile_avatar(body: ProfileAvatarBody, tg_id: TelegramId):
    return core_service.set_profile_avatar(tg_id, body)


@router.post("/api/profile/nickname-colors/{color}")
def buy_nickname_color(color: str, tg_id: TelegramId):
    return core_service.buy_nickname_color(tg_id, color)


@router.post("/api/profile/frame")
def set_profile_frame(body: ProfileFrameBody, tg_id: TelegramId):
    return core_service.set_profile_frame(tg_id, body)


@router.post("/api/profile/frames/{frame}")
def buy_profile_frame(frame: str, tg_id: TelegramId):
    return core_service.buy_profile_frame(tg_id, frame)


@router.post("/api/profile/wallpaper")
def set_profile_wallpaper(body: ProfileWallpaperBody, tg_id: TelegramId):
    return core_service.set_profile_wallpaper(tg_id, body)


@router.post("/api/profile/wallpapers/{wallpaper}")
def buy_profile_wallpaper(wallpaper: str, tg_id: TelegramId):
    return core_service.buy_profile_wallpaper(tg_id, wallpaper)


@router.post("/api/register")
def register(body: RegisterBody, tg_id: TelegramId):
    return core_service.register(tg_id, body)
