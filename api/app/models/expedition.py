from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db.base import Base
from api.app.models.enums import ExpeditionOutcome, GeneLevel, HabitatType


class Expedition(Base):
    __tablename__ = "expeditions"
    __table_args__ = (UniqueConstraint("captured_animal_id"), UniqueConstraint("lost_animal_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    player_season_id: Mapped[int] = mapped_column(ForeignKey("player_seasons.id", ondelete="CASCADE"), index=True)
    target_terrain_type: Mapped[HabitatType] = mapped_column(Enum(HabitatType, native_enum=False, length=32), index=True)
    outcome: Mapped[ExpeditionOutcome] = mapped_column(Enum(ExpeditionOutcome, native_enum=False, length=16), default=ExpeditionOutcome.PENDING, index=True)
    wild_survival_gene: Mapped[GeneLevel | None] = mapped_column(Enum(GeneLevel, native_enum=False, length=16), nullable=True)
    wild_breeding_gene: Mapped[GeneLevel | None] = mapped_column(Enum(GeneLevel, native_enum=False, length=16), nullable=True)
    wild_appearance_gene: Mapped[GeneLevel | None] = mapped_column(Enum(GeneLevel, native_enum=False, length=16), nullable=True)
    wild_size_gene: Mapped[GeneLevel | None] = mapped_column(Enum(GeneLevel, native_enum=False, length=16), nullable=True)
    party_power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wild_power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captured_animal_id: Mapped[str | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)
    lost_animal_id: Mapped[str | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolves_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    player_season = relationship("PlayerSeason", back_populates="expeditions")
    party_members = relationship("ExpeditionPartyMember", back_populates="expedition", cascade="all, delete-orphan")
    captured_animal = relationship("Animal", foreign_keys=[captured_animal_id])
    lost_animal = relationship("Animal", foreign_keys=[lost_animal_id])


class ExpeditionPartyMember(Base):
    __tablename__ = "expedition_party_members"
    __table_args__ = (UniqueConstraint("expedition_id", "animal_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), index=True)
    animal_id: Mapped[str] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), index=True)
    slot_order: Mapped[int] = mapped_column(Integer)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    expedition = relationship("Expedition", back_populates="party_members")
    animal = relationship("Animal", back_populates="expedition_memberships")
