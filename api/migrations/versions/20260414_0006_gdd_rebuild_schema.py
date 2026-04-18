"""Rebuild the schema for Merchant's Menagerie GDD.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_TABLES = [
    "transfer_money_claims",
    "transfer_money",
    "donates",
    "user_achievement_progress",
    "user_achievements",
    "requests_to_unity",
    "unity_members",
    "unity",
    "random_merchants",
    "sick_animal_events",
    "items",
    "item_logs",
    "webapp_extra",
    "web_sessions",
    "gamers",
    "games",
    "user_aviary_states",
    "aviaries",
    "user_animal_states",
    "animals",
    "values",
    "users",
    "player_habitats",
    "player_seasons",
    "seasons",
    "players",
    "pack_openings",
    "breeding_attempts",
    "expeditions",
    "expedition_party_members",
]


def upgrade() -> None:
    conn = op.get_bind()
    is_mysql = conn.dialect.name == "mysql"
    if is_mysql:
        conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
    for table_name in LEGACY_TABLES:
        conn.execute(sa.text(f"DROP TABLE IF EXISTS `{table_name}`"))
    if is_mysql:
        conn.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("nickname", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("telegram_id", name=op.f("uq_players_telegram_id")),
        sa.UniqueConstraint("nickname", name=op.f("uq_players_nickname")),
    )
    op.create_index(op.f("ix_players_telegram_id"), "players", ["telegram_id"], unique=False)

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("ordinal", name=op.f("uq_seasons_ordinal")),
    )
    op.create_index(op.f("ix_seasons_ordinal"), "seasons", ["ordinal"], unique=False)
    op.create_index(op.f("ix_seasons_starts_at"), "seasons", ["starts_at"], unique=False)
    op.create_index(op.f("ix_seasons_ends_at"), "seasons", ["ends_at"], unique=False)

    op.create_table(
        "player_seasons",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("balance_coins", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("last_income_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE", name=op.f("fk_player_seasons_player_id_players")),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE", name=op.f("fk_player_seasons_season_id_seasons")),
        sa.UniqueConstraint("player_id", "season_id", name="uq_player_seasons_player_id_season_id"),
    )
    op.create_index(op.f("ix_player_seasons_player_id"), "player_seasons", ["player_id"], unique=False)
    op.create_index(op.f("ix_player_seasons_season_id"), "player_seasons", ["season_id"], unique=False)

    op.create_table(
        "player_habitats",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_season_id", sa.Integer(), nullable=False),
        sa.Column("terrain_type", sa.String(length=32), nullable=False),
        sa.Column("unlock_order", sa.Integer(), nullable=False),
        sa.Column("purchase_price", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], ondelete="CASCADE", name=op.f("fk_player_habitats_player_season_id_player_seasons")),
        sa.UniqueConstraint("player_season_id", "terrain_type", name="uq_player_habitats_player_season_id_terrain_type"),
    )
    op.create_index(op.f("ix_player_habitats_player_season_id"), "player_habitats", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_player_habitats_terrain_type"), "player_habitats", ["terrain_type"], unique=False)

    op.create_table(
        "animals",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("player_season_id", sa.Integer(), nullable=False),
        sa.Column("parent_one_id", sa.String(length=36), nullable=True),
        sa.Column("parent_two_id", sa.String(length=36), nullable=True),
        sa.Column("current_habitat_id", sa.Integer(), nullable=True),
        sa.Column("origin_type", sa.String(length=32), nullable=False),
        sa.Column("survival_gene", sa.String(length=16), nullable=False),
        sa.Column("breeding_gene", sa.String(length=16), nullable=False),
        sa.Column("appearance_gene", sa.String(length=16), nullable=False),
        sa.Column("size_gene", sa.String(length=16), nullable=False),
        sa.Column("habitat_preference", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_breeding_day", sa.Integer(), nullable=True),
        sa.Column("born_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dies_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("died_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], ondelete="CASCADE", name=op.f("fk_animals_player_season_id_player_seasons")),
        sa.ForeignKeyConstraint(["parent_one_id"], ["animals.id"], ondelete="SET NULL", name=op.f("fk_animals_parent_one_id_animals")),
        sa.ForeignKeyConstraint(["parent_two_id"], ["animals.id"], ondelete="SET NULL", name=op.f("fk_animals_parent_two_id_animals")),
        sa.ForeignKeyConstraint(["current_habitat_id"], ["player_habitats.id"], ondelete="SET NULL", name=op.f("fk_animals_current_habitat_id_player_habitats")),
    )
    op.create_index(op.f("ix_animals_player_season_id"), "animals", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_animals_current_habitat_id"), "animals", ["current_habitat_id"], unique=False)
    op.create_index(op.f("ix_animals_status"), "animals", ["status"], unique=False)
    op.create_index(op.f("ix_animals_dies_at"), "animals", ["dies_at"], unique=False)

    op.create_table(
        "pack_openings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_season_id", sa.Integer(), nullable=False),
        sa.Column("season_day", sa.Integer(), nullable=False),
        sa.Column("opening_type", sa.String(length=16), nullable=False),
        sa.Column("price_paid", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("reward_animal_id", sa.String(length=36), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], ondelete="CASCADE", name=op.f("fk_pack_openings_player_season_id_player_seasons")),
        sa.ForeignKeyConstraint(["reward_animal_id"], ["animals.id"], ondelete="CASCADE", name=op.f("fk_pack_openings_reward_animal_id_animals")),
        sa.UniqueConstraint("reward_animal_id", name="uq_pack_openings_reward_animal_id"),
    )
    op.create_index(op.f("ix_pack_openings_player_season_id"), "pack_openings", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_pack_openings_season_day"), "pack_openings", ["season_day"], unique=False)
    op.create_index(op.f("ix_pack_openings_opening_type"), "pack_openings", ["opening_type"], unique=False)

    op.create_table(
        "breeding_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_season_id", sa.Integer(), nullable=False),
        sa.Column("season_day", sa.Integer(), nullable=False),
        sa.Column("first_parent_id", sa.String(length=36), nullable=False),
        sa.Column("second_parent_id", sa.String(length=36), nullable=False),
        sa.Column("success_probability", sa.Numeric(6, 4), nullable=False),
        sa.Column("was_successful", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("child_animal_id", sa.String(length=36), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], ondelete="CASCADE", name=op.f("fk_breeding_attempts_player_season_id_player_seasons")),
        sa.ForeignKeyConstraint(["first_parent_id"], ["animals.id"], ondelete="CASCADE", name=op.f("fk_breeding_attempts_first_parent_id_animals")),
        sa.ForeignKeyConstraint(["second_parent_id"], ["animals.id"], ondelete="CASCADE", name=op.f("fk_breeding_attempts_second_parent_id_animals")),
        sa.ForeignKeyConstraint(["child_animal_id"], ["animals.id"], ondelete="SET NULL", name=op.f("fk_breeding_attempts_child_animal_id_animals")),
        sa.UniqueConstraint("child_animal_id", name="uq_breeding_attempts_child_animal_id"),
    )
    op.create_index(op.f("ix_breeding_attempts_player_season_id"), "breeding_attempts", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_breeding_attempts_season_day"), "breeding_attempts", ["season_day"], unique=False)
    op.create_index(op.f("ix_breeding_attempts_first_parent_id"), "breeding_attempts", ["first_parent_id"], unique=False)
    op.create_index(op.f("ix_breeding_attempts_second_parent_id"), "breeding_attempts", ["second_parent_id"], unique=False)

    op.create_table(
        "expeditions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_season_id", sa.Integer(), nullable=False),
        sa.Column("target_terrain_type", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("wild_survival_gene", sa.String(length=16), nullable=True),
        sa.Column("wild_breeding_gene", sa.String(length=16), nullable=True),
        sa.Column("wild_appearance_gene", sa.String(length=16), nullable=True),
        sa.Column("wild_size_gene", sa.String(length=16), nullable=True),
        sa.Column("party_power", sa.Integer(), nullable=True),
        sa.Column("wild_power", sa.Integer(), nullable=True),
        sa.Column("captured_animal_id", sa.String(length=36), nullable=True),
        sa.Column("lost_animal_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolves_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["player_season_id"], ["player_seasons.id"], ondelete="CASCADE", name=op.f("fk_expeditions_player_season_id_player_seasons")),
        sa.ForeignKeyConstraint(["captured_animal_id"], ["animals.id"], ondelete="SET NULL", name=op.f("fk_expeditions_captured_animal_id_animals")),
        sa.ForeignKeyConstraint(["lost_animal_id"], ["animals.id"], ondelete="SET NULL", name=op.f("fk_expeditions_lost_animal_id_animals")),
        sa.UniqueConstraint("captured_animal_id", name="uq_expeditions_captured_animal_id"),
        sa.UniqueConstraint("lost_animal_id", name="uq_expeditions_lost_animal_id"),
    )
    op.create_index(op.f("ix_expeditions_player_season_id"), "expeditions", ["player_season_id"], unique=False)
    op.create_index(op.f("ix_expeditions_target_terrain_type"), "expeditions", ["target_terrain_type"], unique=False)
    op.create_index(op.f("ix_expeditions_outcome"), "expeditions", ["outcome"], unique=False)
    op.create_index(op.f("ix_expeditions_resolves_at"), "expeditions", ["resolves_at"], unique=False)

    op.create_table(
        "expedition_party_members",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("expedition_id", sa.Integer(), nullable=False),
        sa.Column("animal_id", sa.String(length=36), nullable=False),
        sa.Column("slot_order", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], ondelete="CASCADE", name=op.f("fk_expedition_party_members_expedition_id_expeditions")),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE", name=op.f("fk_expedition_party_members_animal_id_animals")),
        sa.UniqueConstraint("expedition_id", "animal_id", name="uq_expedition_party_members_expedition_id_animal_id"),
    )
    op.create_index(op.f("ix_expedition_party_members_expedition_id"), "expedition_party_members", ["expedition_id"], unique=False)
    op.create_index(op.f("ix_expedition_party_members_animal_id"), "expedition_party_members", ["animal_id"], unique=False)


def downgrade() -> None:
    for table_name in [
        "expedition_party_members",
        "expeditions",
        "breeding_attempts",
        "pack_openings",
        "animals",
        "player_habitats",
        "player_seasons",
        "seasons",
        "players",
    ]:
        op.drop_table(table_name)
