from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base
from api.app.models.enums import HabitatType


class PlayerHabitat(Base):
    __tablename__ = "player_habitats"
    __table_args__ = (UniqueConstraint("player_season_id", "terrain_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_season_id: Mapped[int] = mapped_column(ForeignKey("player_seasons.id", ondelete="CASCADE"), index=True)
    terrain_type: Mapped[HabitatType] = mapped_column(Enum(HabitatType, native_enum=False, length=32), index=True)
    unlock_order: Mapped[int] = mapped_column(Integer)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player_season = relationship("PlayerSeason", back_populates="habitats")
    residents = relationship("Animal", back_populates="current_habitat")
