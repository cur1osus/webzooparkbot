from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterBody(BaseModel):
    nickname: str = Field(min_length=1, max_length=32)
    ref_code: str | None = None


class NicknameUpdateBody(BaseModel):
    nickname: str = Field(min_length=1, max_length=32)


class NicknameColorBody(BaseModel):
    color: str = Field(min_length=1, max_length=16)


class ProfileAvatarBody(BaseModel):
    avatar: str | None = Field(default=None, max_length=64)


class ProfileFrameBody(BaseModel):
    frame: str = Field(min_length=1, max_length=24)


class ProfileWallpaperBody(BaseModel):
    wallpaper: str = Field(min_length=1, max_length=24)


class ThemeBody(BaseModel):
    theme: str = Field(min_length=1, max_length=16)
