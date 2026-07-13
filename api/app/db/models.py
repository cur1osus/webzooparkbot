"""Database schema.

Conventions, applied without exception:

* Table names are plural snake_case with no prefix. The web app owns its own database
  (`zoopark`); the Telegram bot lives in `zooparkbot`. The old `zoopark_*` prefix and
  the compat-copy bootstrap existed only for a time when they shared one.
* Every table has a surrogate `id`, except link tables, which use the natural composite.
* A foreign key is `<entity>_id` and is declared as one, with an explicit ON DELETE.
* Timestamps end in `_at`, are `UtcDateTime`, and are timezone-aware in Python.
* Money is a non-negative `BigInteger`. Currency only moves through `ledger.grant()`.
* Anything with a fixed set of values gets a CHECK constraint, so a typo in the domain
  layer fails at the database rather than sitting in a row forever.

Derived state is never stored twice. `animals` has no `is_alive` flag: an animal is
alive iff `removed_at IS NULL AND (dies_at IS NULL OR dies_at > NOW())`. The old flag
had to be swept by `expire_dead_pack_animals`, and every endpoint that forgot to call it
served dead animals as live ones.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from api.app.zoopark.catalog import (
    CURRENCIES,
    GAME_KINDS,
    GENE_TIERS,
    HABITATS,
    ITEM_RARITIES,
    PROPERTY_KINDS,
    RARITIES,
)


class UtcDateTime(TypeDecorator):
    """Stores naive UTC (what MySQL DATETIME holds) and hands back aware UTC.

    Every `datetime` crossing this boundary is timezone-aware. The previous schema used
    a bare `DateTime`, so the domain layer was littered with `value.replace(tzinfo=utc)`
    and each new call site was a chance to forget.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime reached the database; use utcnow()")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


# SQLite only auto-increments an `INTEGER PRIMARY KEY`, never a `BIGINT` one. The variant
# keeps MySQL on BIGINT while letting the test suite run the real schema in memory.
BigPK = BigInteger().with_variant(Integer, "sqlite")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _one_of(column: str, values: tuple[str, ...]) -> str:
    joined = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({joined})"


MYSQL = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}


class Base(DeclarativeBase):
    pass


# ─── Identity ─────────────────────────────────────────────────────────────────


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        CheckConstraint(_one_of("status", ("active", "banned")), name="ck_players_status"),
        CheckConstraint("balance_rub >= 0", name="ck_players_balance_rub"),
        CheckConstraint("balance_usd >= 0", name="ck_players_balance_usd"),
        CheckConstraint("balance_paw >= 0", name="ck_players_balance_paw"),
        CheckConstraint("vet_level BETWEEN 0 AND 5", name="ck_players_vet_level"),
        CheckConstraint("genetics_level BETWEEN 0 AND 5", name="ck_players_genetics_level"),
        Index("ix_players_income", "income_rub_per_min"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Unique in the schema, not just in a racy `SELECT … WHERE nickname = ?` beforehand.
    nickname: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    profile_emoji: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nickname_color: Mapped[str] = mapped_column(String(16), nullable=False, default="ivory")
    profile_frame: Mapped[str] = mapped_column(String(24), nullable=False, default="none")
    profile_wallpaper: Mapped[str] = mapped_column(String(24), nullable=False, default="none")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    registered_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)

    referred_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True
    )

    balance_rub: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    balance_usd: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    balance_paw: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    vet_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    genetics_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # Cached so the leaderboard is an indexed read instead of a full scan of every
    # animal of every player. Recomputed by `income.sync_player_income` on any change
    # to the zoo, and on every currency-moving request.
    income_rub_per_min: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    upkeep_rub_per_min: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    income_synced_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)

    referrer: Mapped[Player | None] = relationship("Player", remote_side=[id])
    animals: Mapped[list[Animal]] = relationship(
        "Animal", back_populates="player", foreign_keys="Animal.player_id"
    )
    items: Mapped[list[Item]] = relationship("Item", back_populates="player")


class PlayerCosmetic(Base):
    __tablename__ = "player_cosmetics"
    __table_args__ = (MYSQL,)

    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    cosmetic_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    purchased_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


# ─── Seasons ──────────────────────────────────────────────────────────────────


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint(_one_of("status", ("active", "finished")), name="ck_seasons_status"),
        Index("ix_seasons_status_ends_at", "status", "ends_at"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    starts_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


class SeasonPlayer(Base):
    __tablename__ = "season_players"
    __table_args__ = (Index("ix_season_players_player", "player_id"), MYSQL)

    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("seasons.id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


# ─── Catalogue ────────────────────────────────────────────────────────────────


class Species(Base):
    """Seeded from `catalog.SPECIES`. Cosmetic: GDD §3 keeps species out of the income
    formula entirely. It exists so animals can carry a real foreign key rather than an
    integer that happens to index a Python list."""

    __tablename__ = "species"
    __table_args__ = (
        CheckConstraint(_one_of("rarity", RARITIES), name="ck_species_rarity"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False)
    rarity: Mapped[str] = mapped_column(String(16), nullable=False)


# ─── Zoo ──────────────────────────────────────────────────────────────────────


class Locality(Base):
    __tablename__ = "localities"
    __table_args__ = (
        UniqueConstraint("player_id", "season_id", "habitat", name="uq_localities_player_season_habitat"),
        CheckConstraint(_one_of("habitat", HABITATS), name="ck_localities_habitat"),
        CheckConstraint("level BETWEEN 0 AND 3", name="ck_localities_level"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    habitat: Mapped[str] = mapped_column(String(16), nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    price_paid_rub: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    purchased_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)

    animals: Mapped[list[Animal]] = relationship("Animal", back_populates="locality")


class Animal(Base):
    """One row per animal. Alive iff `removed_at IS NULL AND (dies_at IS NULL OR dies_at > now)`."""

    __tablename__ = "animals"
    __table_args__ = (
        CheckConstraint(_one_of("gene_survival", GENE_TIERS), name="ck_animals_gene_survival"),
        CheckConstraint(_one_of("gene_reproduction", GENE_TIERS), name="ck_animals_gene_reproduction"),
        CheckConstraint(_one_of("gene_appearance", GENE_TIERS), name="ck_animals_gene_appearance"),
        CheckConstraint(_one_of("gene_size", GENE_TIERS), name="ck_animals_gene_size"),
        CheckConstraint(_one_of("habitat", HABITATS), name="ck_animals_habitat"),
        CheckConstraint(
            _one_of("origin", ("pack", "merchant", "breeding", "expedition")),
            name="ck_animals_origin",
        ),
        CheckConstraint(
            "removal_reason IS NULL OR " + _one_of("removal_reason", ("expedition_loss", "released")),
            name="ck_animals_removal_reason",
        ),
        Index("ix_animals_player_season_alive", "player_id", "season_id", "removed_at", "dies_at"),
        Index("ix_animals_locality", "locality_id"),
        Index("ix_animals_species", "species_id"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    species_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("species.id"), nullable=False)
    # Individual pet name (Renaissance-figure pool) so duplicate species are distinguishable.
    # Nullable for animals created before names existed; the client falls back to the species.
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    locality_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("localities.id", ondelete="SET NULL"), nullable=True
    )

    gene_survival: Mapped[str] = mapped_column(String(8), nullable=False)
    gene_reproduction: Mapped[str] = mapped_column(String(8), nullable=False)
    gene_appearance: Mapped[str] = mapped_column(String(8), nullable=False)
    gene_size: Mapped[str] = mapped_column(String(8), nullable=False)
    habitat: Mapped[str] = mapped_column(String(16), nullable=False)

    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    dies_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    removal_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # A sick animal halves its own income until cured. 0..1 per animal, so a column,
    # not the `sick_events` table it used to be.
    sick_since: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)

    last_bred_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    parent_a_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("animals.id", ondelete="SET NULL"), nullable=True
    )
    parent_b_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("animals.id", ondelete="SET NULL"), nullable=True
    )

    player: Mapped[Player] = relationship("Player", back_populates="animals", foreign_keys=[player_id])
    species: Mapped[Species] = relationship("Species")
    locality: Mapped[Locality | None] = relationship("Locality", back_populates="animals")


class PackOpening(Base):
    __tablename__ = "pack_openings"
    __table_args__ = (Index("ix_pack_openings_player_opened", "player_id", "opened_at"), MYSQL)

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    animal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    price_paid_rub: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    opened_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


class BreedingAttempt(Base):
    __tablename__ = "breeding_attempts"
    __table_args__ = (Index("ix_breeding_attempts_player_created", "player_id", "created_at"), MYSQL)

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    parent_a_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    parent_b_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    child_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("animals.id", ondelete="SET NULL"), nullable=True)
    success_rate_pct: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


class Expedition(Base):
    """GDD §7: only one active expedition at a time.

    `active_marker` is a stored generated column that is 1 while the expedition is
    unresolved and NULL afterwards. MySQL treats NULLs as distinct in a unique index,
    so the constraint below makes "one active expedition per player per season" an
    invariant of the database rather than a check the domain layer might forget.
    """

    __tablename__ = "expeditions"
    __table_args__ = (
        UniqueConstraint("player_id", "season_id", "active_marker", name="uq_expeditions_one_active"),
        CheckConstraint(
            "outcome IS NULL OR " + _one_of("outcome", ("victory", "defeat")),
            name="ck_expeditions_outcome",
        ),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    locality_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("localities.id", ondelete="CASCADE"), nullable=False)

    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)

    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    active_marker: Mapped[int | None] = mapped_column(
        SmallInteger, Computed("(case when resolved_at is null then 1 else null end)", persisted=True)
    )

    locality: Mapped[Locality] = relationship("Locality")
    members: Mapped[list[ExpeditionMember]] = relationship(
        "ExpeditionMember", back_populates="expedition", cascade="all, delete-orphan"
    )


class ExpeditionMember(Base):
    __tablename__ = "expedition_members"
    __table_args__ = (Index("ix_expedition_members_animal", "animal_id"), MYSQL)

    expedition_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("expeditions.id", ondelete="CASCADE"), primary_key=True
    )
    animal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("animals.id", ondelete="CASCADE"), primary_key=True
    )

    expedition: Mapped[Expedition] = relationship("Expedition", back_populates="members")
    animal: Mapped[Animal] = relationship("Animal")


class MerchantOffer(Base):
    """Three slots per player per season. The unique key on `slot` is what makes two
    concurrent `GET /api/merchant/animals` unable to conjure six offers."""

    __tablename__ = "merchant_offers"
    __table_args__ = (
        UniqueConstraint("player_id", "season_id", "slot", name="uq_merchant_offers_slot"),
        CheckConstraint("slot >= 1", name="ck_merchant_offers_slot"),
        CheckConstraint(_one_of("habitat", HABITATS), name="ck_merchant_offers_habitat"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    slot: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    species_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("species.id"), nullable=False)
    gene_survival: Mapped[str] = mapped_column(String(8), nullable=False)
    gene_reproduction: Mapped[str] = mapped_column(String(8), nullable=False)
    gene_appearance: Mapped[str] = mapped_column(String(8), nullable=False)
    gene_size: Mapped[str] = mapped_column(String(8), nullable=False)
    habitat: Mapped[str] = mapped_column(String(16), nullable=False)

    discount_pct: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    list_price_rub: Mapped[int] = mapped_column(BigInteger, nullable=False)

    purchased_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)

    species: Mapped[Species] = relationship("Species")


# ─── Forge ────────────────────────────────────────────────────────────────────


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint(_one_of("rarity", ITEM_RARITIES), name="ck_items_rarity"),
        CheckConstraint("level >= 0", name="ck_items_level"),
        Index("ix_items_player_active", "player_id", "is_active"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    rarity: Mapped[str] = mapped_column(String(16), nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)

    player: Mapped[Player] = relationship("Player", back_populates="items")
    properties: Mapped[list[ItemProperty]] = relationship(
        "ItemProperty", back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )
    set_memberships: Mapped[list[ItemSetMember]] = relationship(
        "ItemSetMember", back_populates="item", cascade="all, delete-orphan"
    )


class ItemProperty(Base):
    """One row per effect. Was a JSON blob in `items.properties`, which meant "what
    bonuses does this player have active" required reading and parsing every item.

    `species_id` is set exactly for the per-species kinds (`income_species`) and NULL for
    the rest; the unique key therefore makes merging two items an upsert rather than a
    hand-rolled deduplication.
    """

    __tablename__ = "item_properties"
    __table_args__ = (
        UniqueConstraint("item_id", "kind", "species_id", name="uq_item_properties_item_kind_species"),
        CheckConstraint(_one_of("kind", PROPERTY_KINDS), name="ck_item_properties_kind"),
        CheckConstraint("value > 0", name="ck_item_properties_value"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    species_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("species.id"), nullable=True)

    item: Mapped[Item] = relationship("Item", back_populates="properties")
    species: Mapped[Species | None] = relationship("Species")


class ItemSet(Base):
    __tablename__ = "item_sets"
    __table_args__ = (
        UniqueConstraint("player_id", "name", name="uq_item_sets_player_name"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False, default="⚒️")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)

    members: Mapped[list[ItemSetMember]] = relationship(
        "ItemSetMember", back_populates="item_set", cascade="all, delete-orphan", lazy="selectin"
    )


class ItemSetMember(Base):
    __tablename__ = "item_set_members"
    __table_args__ = (Index("ix_item_set_members_item", "item_id"), MYSQL)

    set_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("item_sets.id", ondelete="CASCADE"), primary_key=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    item_set: Mapped[ItemSet] = relationship("ItemSet", back_populates="members")
    item: Mapped[Item] = relationship("Item", back_populates="set_memberships")


# ─── Clans ────────────────────────────────────────────────────────────────────


class Clan(Base):
    __tablename__ = "clans"
    __table_args__ = (MYSQL,)

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE", name="fk_clans_owner_id"), nullable=False
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)

    members: Mapped[list[ClanMember]] = relationship(
        "ClanMember", back_populates="clan", cascade="all, delete-orphan"
    )


class ClanMember(Base):
    """`UNIQUE(player_id)` is the whole point: a player belongs to at most one clan, and
    the database says so rather than a `user.unity_id` column that nothing constrains."""

    __tablename__ = "clan_members"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_clan_members_player"),
        CheckConstraint(_one_of("role", ("owner", "member")), name="ck_clan_members_role"),
        MYSQL,
    )

    clan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("clans.id", ondelete="CASCADE"), primary_key=True)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="member")
    joined_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)

    clan: Mapped[Clan] = relationship("Clan", back_populates="members")
    player: Mapped[Player] = relationship("Player")


# ─── Games ────────────────────────────────────────────────────────────────────


class Duel(Base):
    __tablename__ = "duels"
    __table_args__ = (
        CheckConstraint(_one_of("kind", GAME_KINDS), name="ck_duels_kind"),
        CheckConstraint(_one_of("status", ("open", "finished", "cancelled")), name="ck_duels_status"),
        CheckConstraint("stake_rub > 0", name="ck_duels_stake"),
        Index("ix_duels_status_created", "status", "created_at"),
        Index("ix_duels_creator", "creator_id"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    stake_rub: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    opponent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    winner_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    creator_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opponent_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class SoloStats(Base):
    """A cache over `ledger`, kept because the profile screen reads it on every load."""

    __tablename__ = "solo_stats"
    __table_args__ = (MYSQL,)

    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    games_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    won_rub: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    lost_rub: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class CocktailRound(Base):
    """`expires_at` is stored rather than derived from `started_at + 24h`: solving the
    puzzle should reset the round at the next UTC midnight, not 24 hours after it began."""

    __tablename__ = "cocktail_rounds"
    __table_args__ = (MYSQL,)

    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    solved_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class DailyBonus(Base):
    """One offer per player per UTC day. `rerolls_used` is what the `bonus_rerolls` item
    property spends; the offer is generated server-side so a reroll cannot be replayed."""

    __tablename__ = "daily_bonuses"
    __table_args__ = (
        UniqueConstraint("player_id", "bonus_date", name="uq_daily_bonuses_player_date"),
        CheckConstraint(_one_of("currency", CURRENCIES), name="ck_daily_bonuses_currency"),
        CheckConstraint("amount > 0", name="ck_daily_bonuses_amount"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    bonus_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rerolls_used: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    claimed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


# ─── Transfers ────────────────────────────────────────────────────────────────


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint("amount_per_claim > 0", name="ck_transfers_amount"),
        CheckConstraint("max_claims > 0", name="ck_transfers_max_claims"),
        CheckConstraint("claims_used >= 0 AND claims_used <= max_claims", name="ck_transfers_claims_used"),
        Index("ix_transfers_sender", "sender_id"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    amount_per_claim: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_claims: Mapped[int] = mapped_column(Integer, nullable=False)
    claims_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class TransferClaim(Base):
    __tablename__ = "transfer_claims"
    __table_args__ = (Index("ix_transfer_claims_player", "player_id"), MYSQL)

    transfer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("transfers.id", ondelete="CASCADE"), primary_key=True)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), primary_key=True)
    amount_rub: Mapped[int] = mapped_column(BigInteger, nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


# ─── Payments and the money trail ─────────────────────────────────────────────


class StarPayment(Base):
    """Ledger of Telegram Stars purchases. `charge_id` as the primary key is what makes
    crediting idempotent under Telegram's retries; `refunded_at` is what stops a player
    from keeping the PawCoins after asking Telegram for their Stars back."""

    __tablename__ = "star_payments"
    __table_args__ = (Index("ix_star_payments_player", "player_id"), MYSQL)

    charge_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    paw_credited: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
    refunded_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class TelegramUpdate(Base):
    """Every update Telegram has already delivered. Makes the webhook idempotent for all
    update kinds, not just the two that happen to touch money."""

    __tablename__ = "telegram_updates"
    __table_args__ = (MYSQL,)

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


class LedgerEntry(Base):
    """Every movement of every currency, for every player.

    Nothing may write `player.balance_*` directly; `ledger.grant()` is the only door.
    `balance_after` makes the invariant checkable with one query per player:
    `SUM(delta) == balance`, which is `test_ledger_reconciles_with_balances`.
    """

    __tablename__ = "ledger"
    __table_args__ = (
        CheckConstraint(_one_of("currency", CURRENCIES), name="ck_ledger_currency"),
        CheckConstraint("delta <> 0", name="ck_ledger_delta"),
        CheckConstraint("balance_after >= 0", name="ck_ledger_balance_after"),
        Index("ix_ledger_player_created", "player_id", "created_at"),
        Index("ix_ledger_reason_created", "reason", "created_at"),
        MYSQL,
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    ref_table: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)


class Treasury(Base):
    """The house's money — bank fees, and whatever the casino wins. One row per currency,
    keyed by the currency itself, so it cannot grow a second row for `id = 1`."""

    __tablename__ = "treasury"
    __table_args__ = (
        CheckConstraint(_one_of("currency", CURRENCIES), name="ck_treasury_currency"),
        MYSQL,
    )

    currency: Mapped[str] = mapped_column(String(8), primary_key=True)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class BankRate(Base):
    """The rub-per-usd rate, one row per minute, append-only.

    A random walk clamped to [RATE_MIN, RATE_MAX], as in the Telegram bot. The previous
    implementation derived the rate from `HMAC(secret, minute)`, which needed a secret to
    stop players precomputing it; state needs no secret. The history also gives the client
    a 24-hour chart for free.
    """

    __tablename__ = "bank_rates"
    __table_args__ = (
        CheckConstraint("rate_rub_per_usd > 0", name="ck_bank_rates_rate"),
        MYSQL,
    )

    # Unix time divided by RATE_PERIOD_SECONDS. Primary key, so two requests racing to
    # advance the rate produce one row, not two.
    period: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    rate_rub_per_usd: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utcnow)
