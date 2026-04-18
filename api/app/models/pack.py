from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base
from api.app.models.enums import PackOpeningType


class PackOpening(Base):
    __tablename__ = "pack_openings"
    __table_args__ = (UniqueConstraint("reward_animal_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_season_id: Mapped[int] = mapped_column(ForeignKey("player_seasons.id", ondelete="CASCADE"), index=True)
    season_day: Mapped[int] = mapped_column(Integer, index=True)
    opening_type: Mapped[PackOpeningType] = mapped_column(Enum(PackOpeningType, native_enum=False, length=16), index=True)
    price_paid: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    reward_animal_id: Mapped[str] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player_season = relationship("PlayerSeason", back_populates="pack_openings")
    reward_animal = relationship("Animal")
