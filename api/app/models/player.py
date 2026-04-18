from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base

if TYPE_CHECKING:
    from api.app.models.achievement_unlock import AchievementUnlock
    from api.app.models.player_profile import PlayerProfile
    from api.app.models.player_season import PlayerSeason


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger(), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    seasons: Mapped[list[PlayerSeason]] = relationship("PlayerSeason", back_populates="player", cascade="all, delete-orphan")
    achievement_unlocks: Mapped[list[AchievementUnlock]] = relationship("AchievementUnlock", back_populates="player", cascade="all, delete-orphan")
    profile = relationship("PlayerProfile", back_populates="player", uselist=False, cascade="all, delete-orphan")
