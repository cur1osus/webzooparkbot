"""Owner-created achievements and their recipients.

Revision ID: 20260716_0022
Revises: 20260716_0021
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql


revision = "20260716_0022"
down_revision = "20260716_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "custom_achievements",
        sa.Column("id", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=180), nullable=False),
        sa.Column("audience", sa.String(length=16), nullable=False),
        sa.Column("image_data", sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql"), nullable=False),
        sa.Column("image_mime", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("audience IN ('all', 'selected')", name="ck_custom_achievements_audience"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_table(
        "custom_achievement_recipients",
        sa.Column("achievement_id", sa.String(length=48), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["achievement_id"], ["custom_achievements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("achievement_id", "player_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_custom_achievement_recipients_player", "custom_achievement_recipients", ["player_id"])


def downgrade() -> None:
    op.drop_index("ix_custom_achievement_recipients_player", table_name="custom_achievement_recipients")
    op.drop_table("custom_achievement_recipients")
    op.drop_table("custom_achievements")
