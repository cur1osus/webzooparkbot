"""Add AI rivals: bot players, their character profiles, and a decision log."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260719_0027"
down_revision = "20260718_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_players_is_bot", "players", ["is_bot"])

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

    op.create_table(
        "bot_plans",
        # SQLite only auto-increments an INTEGER PRIMARY KEY, never a BIGINT one, and the
        # test suite runs this schema on SQLite — same variant the other tables use.
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("character", sa.String(length=32), nullable=False),
        sa.Column("state_before", sa.Text(), nullable=False),
        sa.Column("plan_json", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        # No server_default: MySQL rejects a DEFAULT on TEXT/BLOB (error 1101). SQLite
        # accepts it, so this only shows up against the real database. The Python-side
        # default on the model supplies "[]" on insert.
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


def downgrade() -> None:
    op.drop_index("ix_bot_plans_player_created", table_name="bot_plans")
    op.drop_table("bot_plans")
    op.drop_table("bot_profiles")
    op.drop_index("ix_players_is_bot", table_name="players")
    op.drop_column("players", "is_bot")
