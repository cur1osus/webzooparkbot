from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base


class BreedingAttempt(Base):
    __tablename__ = "breeding_attempts"
    __table_args__ = (UniqueConstraint("child_animal_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_season_id: Mapped[int] = mapped_column(ForeignKey("player_seasons.id", ondelete="CASCADE"), index=True)
    season_day: Mapped[int] = mapped_column(Integer, index=True)
    first_parent_id: Mapped[str] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), index=True)
    second_parent_id: Mapped[str] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), index=True)
    success_probability: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    was_successful: Mapped[bool] = mapped_column(Boolean, default=False)
    child_animal_id: Mapped[str | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player_season = relationship("PlayerSeason", back_populates="breeding_attempts")
    first_parent = relationship("Animal", foreign_keys=[first_parent_id])
    second_parent = relationship("Animal", foreign_keys=[second_parent_id])
    child_animal = relationship("Animal", foreign_keys=[child_animal_id])
