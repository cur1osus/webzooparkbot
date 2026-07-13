"""Initial schema.

The first revision replaced the old `zoopark_*` tables. On a fresh database the legacy
cleanup is a no-op; on a database that can reach this revision it removes only those
obsolete tables, after the deploy backup has completed.

`_drop_legacy()` still runs, so a database that was already serving the old schema comes
out clean rather than carrying twenty-five orphans forever. It is a no-op on a fresh one.

If a database version table points at a revision that is not present in the checkout,
deployment must stop for a reviewed migration/version-table reconciliation. Never drop
the production database as an automated migration step; `deploy.sh` takes a mysqldump
before upgrades and verifies the final head.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_0001"
down_revision = None
branch_labels = None
depends_on = None


# Tables from the schema this one replaces. Dropped only so an already-deployed database
# does not keep them; on a fresh database every one of these is a no-op.
LEGACY_TABLES = (
    "zoopark_bootstrap_meta",
    "zoopark_star_payments",
    "zoopark_transfer_claims",
    "zoopark_transfer_links",
    "zoopark_referrals",
    "zoopark_cocktail_sessions",
    "zoopark_solo_stats",
    "zoopark_mp_games",
    "zoopark_breeding_events",
    "zoopark_expedition_animals",
    "zoopark_expeditions",
    "zoopark_pack_openings",
    "zoopark_pack_animals",
    "zoopark_player_localities",
    "zoopark_merchant_offers",
    "zoopark_sick_events",
    "zoopark_forge_set_items",
    "zoopark_forge_sets",
    "zoopark_items",
    "zoopark_bank_vault",
    "zoopark_player_seasons",
    "zoopark_seasons",
    "zoopark_users",
    "zoopark_unity",
    "animals_info",
)

MYSQL = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

GENE = sa.String(8)
HABITAT = sa.String(16)


def _drop_legacy() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in LEGACY_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table}")
    if bind.dialect.name == "mysql":
        op.execute("SET FOREIGN_KEY_CHECKS = 1")


def upgrade() -> None:
    _drop_legacy()

    op.create_table(
        "players",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("nickname", sa.String(32), nullable=False, unique=True),
        sa.Column("profile_emoji", sa.String(16), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("registered_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("referred_by_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="SET NULL"), nullable=True),
        sa.Column("balance_rub", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("balance_usd", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("balance_paw", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("income_rub_per_min", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("upkeep_rub_per_min", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("income_synced_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'banned')", name="ck_players_status"),
        sa.CheckConstraint("balance_rub >= 0", name="ck_players_balance_rub"),
        sa.CheckConstraint("balance_usd >= 0", name="ck_players_balance_usd"),
        sa.CheckConstraint("balance_paw >= 0", name="ck_players_balance_paw"),
        **MYSQL,
    )
    op.create_index("ix_players_income", "players", ["income_rub_per_min"])
    op.create_index("ix_players_referred_by_id", "players", ["referred_by_id"])

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'finished')", name="ck_seasons_status"),
        **MYSQL,
    )
    op.create_index("ix_seasons_status_ends_at", "seasons", ["status", "ends_at"])

    op.create_table(
        "season_players",
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        **MYSQL,
    )
    op.create_index("ix_season_players_player", "season_players", ["player_id"])

    op.create_table(
        "species",
        sa.Column("id", sa.SmallInteger(), primary_key=True, autoincrement=False),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("emoji", sa.String(16), nullable=False),
        sa.Column("rarity", sa.String(16), nullable=False),
        sa.CheckConstraint("rarity IN ('rare', 'epic', 'mythic', 'legendary')", name="ck_species_rarity"),
        **MYSQL,
    )

    op.create_table(
        "localities",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("habitat", HABITAT, nullable=False),
        sa.Column("price_paid_rub", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("purchased_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("player_id", "season_id", "habitat", name="uq_localities_player_season_habitat"),
        sa.CheckConstraint(
            "habitat IN ('desert', 'mountains', 'forest', 'fields', 'antarctica')",
            name="ck_localities_habitat",
        ),
        **MYSQL,
    )

    gene_checks = [
        sa.CheckConstraint(f"{column} IN ('low', 'medium', 'high')", name=f"ck_animals_{column}")
        for column in ("gene_survival", "gene_reproduction", "gene_appearance", "gene_size")
    ]
    op.create_table(
        "animals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("species_id", sa.SmallInteger(), sa.ForeignKey("species.id"), nullable=False),
        sa.Column("locality_id", sa.BigInteger(), sa.ForeignKey("localities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gene_survival", GENE, nullable=False),
        sa.Column("gene_reproduction", GENE, nullable=False),
        sa.Column("gene_appearance", GENE, nullable=False),
        sa.Column("gene_size", GENE, nullable=False),
        sa.Column("habitat", HABITAT, nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.Column("dies_at", sa.DateTime(), nullable=False),
        sa.Column("removed_at", sa.DateTime(), nullable=True),
        sa.Column("removal_reason", sa.String(16), nullable=True),
        sa.Column("sick_since", sa.DateTime(), nullable=True),
        sa.Column("last_bred_on", sa.Date(), nullable=True),
        sa.Column("parent_a_id", sa.BigInteger(), sa.ForeignKey("animals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_b_id", sa.BigInteger(), sa.ForeignKey("animals.id", ondelete="SET NULL"), nullable=True),
        *gene_checks,
        sa.CheckConstraint(
            "habitat IN ('desert', 'mountains', 'forest', 'fields', 'antarctica')",
            name="ck_animals_habitat",
        ),
        sa.CheckConstraint("origin IN ('pack', 'merchant', 'breeding', 'expedition')", name="ck_animals_origin"),
        sa.CheckConstraint(
            "removal_reason IS NULL OR removal_reason IN ('expedition_loss', 'released')",
            name="ck_animals_removal_reason",
        ),
        **MYSQL,
    )
    op.create_index("ix_animals_player_season_alive", "animals", ["player_id", "season_id", "removed_at", "dies_at"])
    op.create_index("ix_animals_locality", "animals", ["locality_id"])
    op.create_index("ix_animals_species", "animals", ["species_id"])

    op.create_table(
        "pack_openings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("animal_id", sa.BigInteger(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("price_paid_rub", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        **MYSQL,
    )
    op.create_index("ix_pack_openings_player_opened", "pack_openings", ["player_id", "opened_at"])

    op.create_table(
        "breeding_attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_a_id", sa.BigInteger(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_b_id", sa.BigInteger(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_id", sa.BigInteger(), sa.ForeignKey("animals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("success_rate_pct", sa.SmallInteger(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        **MYSQL,
    )
    op.create_index("ix_breeding_attempts_player_created", "breeding_attempts", ["player_id", "created_at"])

    op.create_table(
        "expeditions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locality_id", sa.BigInteger(), sa.ForeignKey("localities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        # NULLs are distinct in a MySQL unique index, so this permits any number of
        # resolved expeditions and exactly one unresolved one.
        sa.Column(
            "active_marker",
            sa.SmallInteger(),
            sa.Computed("(case when resolved_at is null then 1 else null end)", persisted=True),
        ),
        sa.UniqueConstraint("player_id", "season_id", "active_marker", name="uq_expeditions_one_active"),
        sa.CheckConstraint("outcome IS NULL OR outcome IN ('victory', 'defeat')", name="ck_expeditions_outcome"),
        **MYSQL,
    )

    op.create_table(
        "expedition_members",
        sa.Column("expedition_id", sa.BigInteger(), sa.ForeignKey("expeditions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("animal_id", sa.BigInteger(), sa.ForeignKey("animals.id", ondelete="CASCADE"), primary_key=True),
        **MYSQL,
    )
    op.create_index("ix_expedition_members_animal", "expedition_members", ["animal_id"])

    op.create_table(
        "merchant_offers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot", sa.SmallInteger(), nullable=False),
        sa.Column("species_id", sa.SmallInteger(), sa.ForeignKey("species.id"), nullable=False),
        sa.Column("gene_survival", GENE, nullable=False),
        sa.Column("gene_reproduction", GENE, nullable=False),
        sa.Column("gene_appearance", GENE, nullable=False),
        sa.Column("gene_size", GENE, nullable=False),
        sa.Column("habitat", HABITAT, nullable=False),
        sa.Column("discount_pct", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("list_price_rub", sa.BigInteger(), nullable=False),
        sa.Column("purchased_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("player_id", "season_id", "slot", name="uq_merchant_offers_slot"),
        sa.CheckConstraint("slot >= 1", name="ck_merchant_offers_slot"),
        sa.CheckConstraint(
            "habitat IN ('desert', 'mountains', 'forest', 'fields', 'antarctica')",
            name="ck_merchant_offers_habitat",
        ),
        **MYSQL,
    )

    op.create_table(
        "items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rarity", sa.String(16), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("emoji", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "rarity IN ('common', 'rare', 'epic', 'mythical', 'legendary')", name="ck_items_rarity"
        ),
        sa.CheckConstraint("level >= 0", name="ck_items_level"),
        **MYSQL,
    )
    op.create_index("ix_items_player_active", "items", ["player_id", "is_active"])

    op.create_table(
        "item_properties",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("item_id", sa.BigInteger(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("species_id", sa.SmallInteger(), sa.ForeignKey("species.id"), nullable=True),
        sa.UniqueConstraint("item_id", "kind", "species_id", name="uq_item_properties_item_kind_species"),
        sa.CheckConstraint(
            "kind IN ('income_total', 'income_species', 'discount_species', 'discount_locality',"
            " 'discount_bank', 'duel_moves', 'duel_bonus', 'bonus_rerolls')",
            name="ck_item_properties_kind",
        ),
        sa.CheckConstraint("value > 0", name="ck_item_properties_value"),
        **MYSQL,
    )

    op.create_table(
        "item_sets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("emoji", sa.String(16), nullable=False, server_default="⚒️"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("player_id", "name", name="uq_item_sets_player_name"),
        **MYSQL,
    )

    op.create_table(
        "item_set_members",
        sa.Column("set_id", sa.BigInteger(), sa.ForeignKey("item_sets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("item_id", sa.BigInteger(), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.SmallInteger(), nullable=False, server_default="0"),
        **MYSQL,
    )
    op.create_index("ix_item_set_members_item", "item_set_members", ["item_id"])

    op.create_table(
        "clans",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(32), nullable=False, unique=True),
        sa.Column(
            "owner_id",
            sa.BigInteger(),
            sa.ForeignKey("players.id", ondelete="CASCADE", name="fk_clans_owner_id"),
            nullable=False,
        ),
        sa.Column("level", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        **MYSQL,
    )

    op.create_table(
        "clan_members",
        sa.Column("clan_id", sa.BigInteger(), sa.ForeignKey("clans.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        # One clan per player, in the schema rather than in a hope.
        sa.UniqueConstraint("player_id", name="uq_clan_members_player"),
        sa.CheckConstraint("role IN ('owner', 'member')", name="ck_clan_members_role"),
        **MYSQL,
    )

    op.create_table(
        "duels",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("stake_rub", sa.BigInteger(), nullable=False),
        sa.Column("creator_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opponent_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="SET NULL"), nullable=True),
        sa.Column("winner_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("creator_score", sa.Integer(), nullable=True),
        sa.Column("opponent_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('basketball', 'darts', 'bowling', 'dice', 'football')", name="ck_duels_kind"
        ),
        sa.CheckConstraint("status IN ('open', 'finished', 'cancelled')", name="ck_duels_status"),
        sa.CheckConstraint("stake_rub > 0", name="ck_duels_stake"),
        **MYSQL,
    )
    op.create_index("ix_duels_status_created", "duels", ["status", "created_at"])
    op.create_index("ix_duels_creator", "duels", ["creator_id"])

    op.create_table(
        "solo_stats",
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("won_rub", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("lost_rub", sa.BigInteger(), nullable=False, server_default="0"),
        **MYSQL,
    )

    op.create_table(
        "cocktail_rounds",
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("solved_at", sa.DateTime(), nullable=True),
        **MYSQL,
    )

    op.create_table(
        "daily_bonuses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bonus_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("rerolls_used", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("player_id", "bonus_date", name="uq_daily_bonuses_player_date"),
        sa.CheckConstraint("currency IN ('rub', 'usd', 'paw')", name="ck_daily_bonuses_currency"),
        sa.CheckConstraint("amount > 0", name="ck_daily_bonuses_amount"),
        **MYSQL,
    )

    op.create_table(
        "transfers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("sender_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount_per_claim", sa.BigInteger(), nullable=False),
        sa.Column("max_claims", sa.Integer(), nullable=False),
        sa.Column("claims_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("amount_per_claim > 0", name="ck_transfers_amount"),
        sa.CheckConstraint("max_claims > 0", name="ck_transfers_max_claims"),
        sa.CheckConstraint("claims_used >= 0 AND claims_used <= max_claims", name="ck_transfers_claims_used"),
        **MYSQL,
    )
    op.create_index("ix_transfers_sender", "transfers", ["sender_id"])

    op.create_table(
        "transfer_claims",
        sa.Column("transfer_id", sa.BigInteger(), sa.ForeignKey("transfers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("amount_rub", sa.BigInteger(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(), nullable=False),
        **MYSQL,
    )
    op.create_index("ix_transfer_claims_player", "transfer_claims", ["player_id"])

    op.create_table(
        "star_payments",
        sa.Column("charge_id", sa.String(128), primary_key=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("paw_credited", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("refunded_at", sa.DateTime(), nullable=True),
        **MYSQL,
    )
    op.create_index("ix_star_payments_player", "star_payments", ["player_id"])

    op.create_table(
        "telegram_updates",
        sa.Column("update_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        **MYSQL,
    )

    op.create_table(
        "ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("delta", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("ref_table", sa.String(32), nullable=True),
        sa.Column("ref_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("currency IN ('rub', 'usd', 'paw')", name="ck_ledger_currency"),
        sa.CheckConstraint("delta <> 0", name="ck_ledger_delta"),
        sa.CheckConstraint("balance_after >= 0", name="ck_ledger_balance_after"),
        **MYSQL,
    )
    op.create_index("ix_ledger_player_created", "ledger", ["player_id", "created_at"])
    op.create_index("ix_ledger_reason_created", "ledger", ["reason", "created_at"])

    op.create_table(
        "treasury",
        sa.Column("currency", sa.String(8), primary_key=True),
        sa.Column("balance", sa.BigInteger(), nullable=False, server_default="0"),
        sa.CheckConstraint("currency IN ('rub', 'usd', 'paw')", name="ck_treasury_currency"),
        **MYSQL,
    )

    op.create_table(
        "bank_rates",
        sa.Column("period", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("rate_rub_per_usd", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("rate_rub_per_usd > 0", name="ck_bank_rates_rate"),
        **MYSQL,
    )


def downgrade() -> None:
    raise RuntimeError(
        "This is the initial revision. There is nothing to downgrade to; restore the "
        "mysqldump that deploy.sh takes before every migration."
    )
