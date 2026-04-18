from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base


class PlayerSeason(Base):
    __tablename__ = "player_seasons"
    __table_args__ = (UniqueConstraint("player_id", "season_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), index=True)
    balance_coins: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    last_income_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player = relationship("Player", back_populates="seasons")
    season = relationship("Season", back_populates="player_seasons")
    habitats = relationship("PlayerHabitat", back_populates="player_season", cascade="all, delete-orphan")
    animals = relationship("Animal", back_populates="player_season", cascade="all, delete-orphan")
    pack_openings = relationship("PackOpening", back_populates="player_season", cascade="all, delete-orphan")
    breeding_attempts = relationship("BreedingAttempt", back_populates="player_season", cascade="all, delete-orphan")
    expeditions = relationship("Expedition", back_populates="player_season", cascade="all, delete-orphan")
