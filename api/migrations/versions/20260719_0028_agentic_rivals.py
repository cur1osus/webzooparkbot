"""Reshape the rivals' tables for agentic turns.

The rivals no longer produce a plan that a hardcoded recipe carries out; the model calls the
game's tools itself. So a row is now one *turn* — the round trips it took and every tool it
pulled — rather than a plan plus the state before and after it.

`bot_plans` is dropped and recreated rather than migrated column by column: the old shape
holds a handful of rows from the previous design that describe something this code no longer
produces, and carrying them across would leave a table whose older half cannot be read by
anything.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260719_0028"
down_revision = "20260719_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("bot_plans")
    op.create_table(
        "bot_plans",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("character", sa.String(length=32), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=False, server_default="0"),
        # No server_default on TEXT: MySQL rejects it (error 1101).
        sa.Column("tool_calls", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("stopped_because", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_micro_rub", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_bot_plans_player_created", "bot_plans", ["player_id", "created_at"])

    # A turn replaces the old plan/act split, so the two intervals collapse into one.
    #
    # Recreated rather than altered: `plan_every_minutes` and `act_every_minutes` are each
    # named by a CHECK constraint, and neither SQLite nor MySQL will drop a column another
    # constraint still references. Dropping the constraints first is possible on MySQL and
    # not on SQLite, so the shape that works on both is a fresh table. The rows are two
    # lines of configuration that `api.scripts.create_bots` writes back idempotently.
    op.drop_table("bot_profiles")
    op.create_table(
        "bot_profiles",
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("character", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("turn_every_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("wake_hour_utc", sa.SmallInteger(), nullable=False, server_default="6"),
        sa.Column("sleep_hour_utc", sa.SmallInteger(), nullable=False, server_default="22"),
        sa.Column("biography", sa.Text(), nullable=False),
        sa.Column("next_turn_at", sa.DateTime(), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("player_id"),
        sa.CheckConstraint("turn_every_minutes > 0", name="ck_bot_profiles_turn_every"),
        sa.CheckConstraint("wake_hour_utc BETWEEN 0 AND 23", name="ck_bot_profiles_wake_hour"),
        sa.CheckConstraint("sleep_hour_utc BETWEEN 0 AND 23", name="ck_bot_profiles_sleep_hour"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )


def downgrade() -> None:
    op.drop_table("bot_profiles")
    op.create_table(
        "bot_profiles",
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("character", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("plan_every_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("act_every_minutes", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("wake_hour_utc", sa.SmallInteger(), nullable=False, server_default="6"),
        sa.Column("sleep_hour_utc", sa.SmallInteger(), nullable=False, server_default="22"),
        sa.Column("biography", sa.Text(), nullable=False),
        sa.Column("current_plan_id", sa.BigInteger(), nullable=True),
        sa.Column("next_plan_at", sa.DateTime(), nullable=True),
        sa.Column("next_action_at", sa.DateTime(), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("player_id"),
        sa.CheckConstraint("plan_every_minutes > 0", name="ck_bot_profiles_plan_every"),
        sa.CheckConstraint("act_every_minutes > 0", name="ck_bot_profiles_act_every"),
        sa.CheckConstraint("wake_hour_utc BETWEEN 0 AND 23", name="ck_bot_profiles_wake_hour"),
        sa.CheckConstraint("sleep_hour_utc BETWEEN 0 AND 23", name="ck_bot_profiles_sleep_hour"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    op.drop_index("ix_bot_plans_player_created", table_name="bot_plans")
    op.drop_table("bot_plans")
    op.create_table(
        "bot_plans",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("character", sa.String(length=32), nullable=False),
        sa.Column("state_before", sa.Text(), nullable=False),
        sa.Column("plan_json", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("actions_taken", sa.Text(), nullable=False),
        sa.Column("state_after", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_micro_rub", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("source IN ('llm', 'fallback')", name="ck_bot_plans_source"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_bot_plans_player_created", "bot_plans", ["player_id", "created_at"])
