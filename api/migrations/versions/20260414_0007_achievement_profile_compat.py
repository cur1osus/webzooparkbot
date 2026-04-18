"""Add achievement and player profile compatibility tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "player_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("nickname_color", sa.String(length=20), nullable=True),
        sa.Column("active_achievement_cosmetic_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE", name=op.f("fk_player_profiles_player_id_players")),
        sa.UniqueConstraint("player_id", name=op.f("uq_player_profiles_player_id")),
    )
    op.create_index(op.f("ix_player_profiles_player_id"), "player_profiles", ["player_id"], unique=False)

    op.create_table(
        "player_achievements",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("achievement_id", sa.String(length=64), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE", name=op.f("fk_player_achievements_player_id_players")),
        sa.UniqueConstraint("player_id", "achievement_id", name="uq_player_achievements_player_id_achievement_id"),
    )
    op.create_index(op.f("ix_player_achievements_player_id"), "player_achievements", ["player_id"], unique=False)


def downgrade() -> None:
    op.drop_table("player_achievements")
    op.drop_table("player_profiles")
