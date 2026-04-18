"""Add daily bonus, clans, referrals, leaderboard support.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ежедневный бонус
    op.create_table(
        "daily_claims",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("coins_awarded", sa.Numeric(precision=20, scale=2), nullable=False, default=0),
        sa.Column("day_streak", sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.Index("ix_daily_claims_player_id", "player_id"),
    )

    # Кланы
    op.create_table(
        "clans",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("tag", sa.String(length=8), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("tag"),
    )

    op.create_table(
        "clan_members",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("clan_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, default="member"),  # owner / member
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clan_id"], ["clans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("player_id", name="uq_clan_members_player_id"),
        sa.Index("ix_clan_members_clan_id", "clan_id"),
    )

    # Рефералы
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("referrer_id", sa.Integer(), nullable=False),
        sa.Column("referred_id", sa.Integer(), nullable=False),
        sa.Column("reward_claimed", sa.Boolean(), nullable=False, default=False),
        sa.Column("referred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["referrer_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referred_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("referred_id", name="uq_referrals_referred_id"),
        sa.Index("ix_referrals_referrer_id", "referrer_id"),
    )

    # Раздача денег
    op.create_table(
        "money_transfers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("total_coins", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("coins_per_claim", sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column("max_claims", sa.Integer(), nullable=False),
        sa.Column("claims_count", sa.Integer(), nullable=False, default=0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key"),
    )

    op.create_table(
        "transfer_claims",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("transfer_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["transfer_id"], ["money_transfers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("transfer_id", "player_id", name="uq_transfer_claims_transfer_player"),
    )


def downgrade() -> None:
    op.drop_table("transfer_claims")
    op.drop_table("money_transfers")
    op.drop_table("referrals")
    op.drop_table("clan_members")
    op.drop_table("clans")
    op.drop_table("daily_claims")
