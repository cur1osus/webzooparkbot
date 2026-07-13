from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterBody(BaseModel):
    nickname: str = Field(min_length=1, max_length=32)
    ref_code: str | None = None


class NicknameColorBody(BaseModel):
    color: str = Field(min_length=1, max_length=16)


class ProfileAvatarBody(BaseModel):
    avatar: str | None = Field(default=None, max_length=64)
