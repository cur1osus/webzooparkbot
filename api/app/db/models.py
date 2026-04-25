from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "zoopark_users"
    __table_args__ = (
        Index("idx_unity_id", "unity_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_user = Column(BigInteger, nullable=False, unique=True)
    nickname = Column(String(64), nullable=False)
    date_reg = Column(DateTime, nullable=False)
    paw_coins = Column(BigInteger, nullable=False, default=0)
    rub = Column(BigInteger, nullable=False, default=0)
    usd = Column(BigInteger, nullable=False, default=0)
    sub_on_chat = Column(SmallInteger, nullable=False, default=0)
    sub_on_channel = Column(SmallInteger, nullable=False, default=0)
    bonus = Column(SmallInteger, nullable=False, default=1)
    unity_id = Column(Integer, ForeignKey("zoopark_unity.idpk"), nullable=True)
    is_banned = Column(SmallInteger, nullable=False, default=0)
    balance_seq = Column(BigInteger, nullable=False, default=0)
    data_version = Column(BigInteger, nullable=False, default=0)
    bonus_notify_msg_id = Column(BigInteger, nullable=True)
    profile_emoji = Column(String(20), nullable=True)
    last_income_at = Column(DateTime, nullable=True)

    clan = relationship("Unity", foreign_keys=[unity_id], back_populates="members")
    player_seasons = relationship("PlayerSeason", back_populates="user")
    pack_animals = relationship("PackAnimal", foreign_keys="PackAnimal.user_id", back_populates="user")
    localities = relationship("Locality", back_populates="user")
    items = relationship("Item", back_populates="user")
    forge_sets = relationship("ForgeSet", back_populates="user")


class Season(Base):
    __tablename__ = "zoopark_seasons"
    __table_args__ = (
        Index("idx_status", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    status = Column(String(16), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False)

    players = relationship("PlayerSeason", back_populates="season")
    animals = relationship("PackAnimal", back_populates="season")
    localities = relationship("Locality", back_populates="season")
    expeditions = relationship("Expedition", back_populates="season")


class PlayerSeason(Base):
    __tablename__ = "zoopark_player_seasons"
    __table_args__ = (
        Index("idx_season_id", "season_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("zoopark_users.id"), primary_key=True)
    season_id = Column(Integer, ForeignKey("zoopark_seasons.id"), primary_key=True)
    joined_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="player_seasons")
    season = relationship("Season", back_populates="players")


class AnimalInfo(Base):
    __tablename__ = "animals_info"
    __table_args__ = (
        UniqueConstraint("name", name="uq_animals_info_name"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    price = Column(BigInteger, nullable=False)
    income = Column(BigInteger, nullable=False)

    pack_animals = relationship("PackAnimal", back_populates="animal_info")


class Item(Base):
    __tablename__ = "zoopark_items"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    emoji = Column(String(20), nullable=False)
    name = Column(String(64), nullable=False)
    lvl = Column(Integer, nullable=False, default=1)
    properties = Column(Text, nullable=True)
    rarity = Column(String(20), nullable=False, default="common")
    is_active = Column(SmallInteger, nullable=False, default=0)

    user = relationship("User", back_populates="items")
    forge_set_links = relationship("ForgeSetItem", back_populates="item")


class ForgeSet(Base):
    __tablename__ = "zoopark_forge_sets"
    __table_args__ = (
        UniqueConstraint("user_id", "set_key", name="uq_user_forge_set_key"),
        Index("idx_user_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    set_key = Column(String(32), nullable=False)
    name = Column(String(32), nullable=False)
    icon = Column(String(20), nullable=False, default="⚒️")
    created_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="forge_sets")
    items = relationship("ForgeSetItem", back_populates="forge_set", cascade="all, delete-orphan")


class ForgeSetItem(Base):
    __tablename__ = "zoopark_forge_set_items"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    set_id = Column(Integer, ForeignKey("zoopark_forge_sets.id"), primary_key=True)
    item_id = Column(Integer, ForeignKey("zoopark_items.id"), primary_key=True)
    position = Column(Integer, nullable=False, default=0)

    forge_set = relationship("ForgeSet", back_populates="items")
    item = relationship("Item", back_populates="forge_set_links")


class Unity(Base):
    __tablename__ = "zoopark_unity"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    idpk = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(BigInteger, nullable=False, unique=True)
    name = Column(String(64), nullable=False, unique=True)
    level = Column(Integer, nullable=False, default=1)
    owner_id = Column(Integer, ForeignKey("zoopark_users.id", use_alter=True, name="fk_zoopark_unity_owner_id"), nullable=False)

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("User", foreign_keys="User.unity_id", back_populates="clan")


class SickEvent(Base):
    __tablename__ = "zoopark_sick_events"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    animal_id = Column(Integer, ForeignKey("zoopark_pack_animals.id"), nullable=False)
    since = Column(DateTime, nullable=False)
    penalty_rub_per_min = Column(BigInteger, nullable=False, default=500)

    animal = relationship("PackAnimal")


class MpGame(Base):
    __tablename__ = "zoopark_mp_games"
    __table_args__ = (
        Index("idx_status", "status"),
        Index("idx_creator_id", "creator_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_type = Column(String(20), nullable=False)
    bet_rub = Column(BigInteger, nullable=False)
    creator_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    opponent_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=True)
    status = Column(String(10), nullable=False, default="open")
    creator_score = Column(Integer, nullable=True)
    opponent_score = Column(Integer, nullable=True)
    winner_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)


class SoloStats(Base):
    __tablename__ = "zoopark_solo_stats"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    user_id = Column(Integer, ForeignKey("zoopark_users.id"), primary_key=True)
    games_played = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    total_won = Column(BigInteger, nullable=False, default=0)
    total_lost = Column(BigInteger, nullable=False, default=0)


class CocktailSession(Base):
    __tablename__ = "zoopark_cocktail_sessions"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    user_id = Column(Integer, ForeignKey("zoopark_users.id"), primary_key=True)
    secret = Column(Text, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    won = Column(SmallInteger, nullable=False, default=0)
    started_at = Column(DateTime, nullable=False)


class TransferLink(Base):
    __tablename__ = "zoopark_transfer_links"
    __table_args__ = (
        Index("idx_creator_id", "creator_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    link_key = Column(String(32), nullable=False, unique=True)
    creator_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    total_amount = Column(BigInteger, nullable=False)
    rub_per_claim = Column(BigInteger, nullable=False)
    max_claims = Column(Integer, nullable=False)
    claims = Column(Integer, nullable=False, default=0)
    active = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False)


class Merchant(Base):
    __tablename__ = "zoopark_merchant_offers"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_season_id", "season_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    season_id = Column(Integer, ForeignKey("zoopark_seasons.id"), nullable=False)
    animal_info_id = Column(Integer, ForeignKey("animals_info.id"), nullable=False)
    survival = Column(String(10), nullable=False)
    reproduction = Column(String(10), nullable=False)
    appearance = Column(String(10), nullable=False)
    size_trait = Column(String(10), nullable=False)
    habitat = Column(String(15), nullable=False)
    discount = Column(Integer, nullable=False, default=0)
    price = Column(BigInteger, nullable=False, default=0)
    price_with_discount = Column(BigInteger, nullable=False, default=0)
    bought = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    animal_info = relationship("AnimalInfo")


class PackAnimal(Base):
    __tablename__ = "zoopark_pack_animals"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_season_id", "season_id"),
        Index("idx_locality_id", "locality_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    season_id = Column(Integer, ForeignKey("zoopark_seasons.id"), nullable=False)
    animal_info_id = Column(Integer, ForeignKey("animals_info.id"), nullable=False)
    survival = Column(String(10), nullable=False)
    reproduction = Column(String(10), nullable=False)
    appearance = Column(String(10), nullable=False)
    size_trait = Column(String(10), nullable=False)
    habitat = Column(String(15), nullable=False)
    source = Column(String(20), nullable=False, default="pack")
    parent_1_id = Column(Integer, ForeignKey("zoopark_pack_animals.id"), nullable=True)
    parent_2_id = Column(Integer, ForeignKey("zoopark_pack_animals.id"), nullable=True)
    is_alive = Column(SmallInteger, nullable=False, default=1)
    acquired_at = Column(DateTime, nullable=False)
    dies_at = Column(DateTime, nullable=True)
    locality_id = Column(Integer, ForeignKey("zoopark_player_localities.id"), nullable=True)
    last_bred_date = Column(Date, nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="pack_animals")
    season = relationship("Season", back_populates="animals")
    animal_info = relationship("AnimalInfo", back_populates="pack_animals")
    locality = relationship("Locality", back_populates="animals")
    parent_1 = relationship("PackAnimal", remote_side=[id], foreign_keys=[parent_1_id])
    parent_2 = relationship("PackAnimal", remote_side=[id], foreign_keys=[parent_2_id])


class PackOpening(Base):
    __tablename__ = "zoopark_pack_openings"
    __table_args__ = (
        Index("idx_user_season_opened", "user_id", "season_id", "opened_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    season_id = Column(Integer, ForeignKey("zoopark_seasons.id"), nullable=False)
    animal_id = Column(Integer, ForeignKey("zoopark_pack_animals.id"), nullable=False)
    opened_at = Column(DateTime, nullable=False)
    price_paid = Column(BigInteger, nullable=False, default=0)
    is_free = Column(Boolean, nullable=False, default=False)

    animal = relationship("PackAnimal")


class Locality(Base):
    __tablename__ = "zoopark_player_localities"
    __table_args__ = (
        UniqueConstraint("user_id", "season_id", "habitat", name="uq_user_season_habitat"),
        Index("idx_user_id", "user_id"),
        Index("idx_season_id", "season_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    season_id = Column(Integer, ForeignKey("zoopark_seasons.id"), nullable=False)
    habitat = Column(String(15), nullable=False)
    created_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="localities")
    season = relationship("Season", back_populates="localities")
    animals = relationship("PackAnimal", back_populates="locality")
    expeditions = relationship("Expedition", back_populates="locality")


class Expedition(Base):
    __tablename__ = "zoopark_expeditions"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_season_id", "season_id"),
        Index("idx_status", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    season_id = Column(Integer, ForeignKey("zoopark_seasons.id"), nullable=False)
    locality_id = Column(Integer, ForeignKey("zoopark_player_localities.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    status = Column(String(10), nullable=False, default="active")
    result_json = Column(Text, nullable=True)
    result_seen = Column(SmallInteger, nullable=False, default=0)

    season = relationship("Season", back_populates="expeditions")
    locality = relationship("Locality", back_populates="expeditions")
    animals = relationship("ExpeditionAnimal", back_populates="expedition", cascade="all, delete-orphan")


class ExpeditionAnimal(Base):
    __tablename__ = "zoopark_expedition_animals"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    expedition_id = Column(Integer, ForeignKey("zoopark_expeditions.id"), primary_key=True)
    animal_id = Column(Integer, ForeignKey("zoopark_pack_animals.id"), primary_key=True)

    expedition = relationship("Expedition", back_populates="animals")
    animal = relationship("PackAnimal")


class BreedingEvent(Base):
    __tablename__ = "zoopark_breeding_events"
    __table_args__ = (
        Index("idx_user_season_created", "user_id", "season_id", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zoopark_users.id"), nullable=False)
    season_id = Column(Integer, ForeignKey("zoopark_seasons.id"), nullable=False)
    parent_1_id = Column(Integer, ForeignKey("zoopark_pack_animals.id"), nullable=False)
    parent_2_id = Column(Integer, ForeignKey("zoopark_pack_animals.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("zoopark_pack_animals.id"), nullable=True)
    success_rate = Column(Integer, nullable=False)
    success = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)


class Referral(Base):
    __tablename__ = "zoopark_referrals"
    __table_args__ = (
        UniqueConstraint("user_id", "referral_id", name="uq_referral_pair"),
        Index("idx_user_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("zoopark_users.id"), primary_key=True)
    referral_id = Column(Integer, ForeignKey("zoopark_users.id"), primary_key=True)


class BootstrapMeta(Base):
    __tablename__ = "zoopark_bootstrap_meta"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    target_table = Column(String(64), primary_key=True)
    copied_at = Column(DateTime, nullable=False)


class BankVault(Base):
    __tablename__ = "zoopark_bank_vault"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = Column(Integer, primary_key=True, default=1)
    usd_balance = Column(BigInteger, nullable=False, default=0)
