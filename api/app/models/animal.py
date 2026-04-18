from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base
from api.app.models.enums import AnimalOriginType, AnimalStatus, GeneLevel, HabitatType


class Animal(Base):
    __tablename__ = "animals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    player_season_id: Mapped[int] = mapped_column(ForeignKey("player_seasons.id", ondelete="CASCADE"), index=True)
    parent_one_id: Mapped[str | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)
    parent_two_id: Mapped[str | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)
    current_habitat_id: Mapped[int | None] = mapped_column(ForeignKey("player_habitats.id", ondelete="SET NULL"), nullable=True, index=True)
    origin_type: Mapped[AnimalOriginType] = mapped_column(Enum(AnimalOriginType, native_enum=False, length=32))
    survival_gene: Mapped[GeneLevel] = mapped_column(Enum(GeneLevel, native_enum=False, length=16))
    breeding_gene: Mapped[GeneLevel] = mapped_column(Enum(GeneLevel, native_enum=False, length=16))
    appearance_gene: Mapped[GeneLevel] = mapped_column(Enum(GeneLevel, native_enum=False, length=16))
    size_gene: Mapped[GeneLevel] = mapped_column(Enum(GeneLevel, native_enum=False, length=16))
    habitat_preference: Mapped[HabitatType] = mapped_column(Enum(HabitatType, native_enum=False, length=32))
    status: Mapped[AnimalStatus] = mapped_column(Enum(AnimalStatus, native_enum=False, length=32), default=AnimalStatus.ACTIVE, index=True)
    last_breeding_day: Mapped[int | None] = mapped_column(nullable=True)
    born_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dies_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    died_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    player_season = relationship("PlayerSeason", back_populates="animals")
    current_habitat = relationship("PlayerHabitat", back_populates="residents")
    parent_one = relationship("Animal", remote_side=[id], foreign_keys=[parent_one_id], post_update=True)
    parent_two = relationship("Animal", remote_side=[id], foreign_keys=[parent_two_id], post_update=True)
    expedition_memberships = relationship("ExpeditionPartyMember", back_populates="animal", cascade="all, delete-orphan")
