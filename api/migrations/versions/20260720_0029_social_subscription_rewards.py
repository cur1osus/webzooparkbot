"""Track reward-community membership and allow subscription clawbacks."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260720_0029"
down_revision = "20260719_0028"
branch_labels = None
depends_on = None


def _drop_check(table: str, name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite cannot alter a CHECK constraint in place; batch mode rebuilds the table
        # while preserving all rows and foreign keys.
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.drop_constraint(name, type_="check")
    else:
        op.drop_constraint(name, table_name=table, type_="check")


def upgrade() -> None:
    _drop_check("players", "ck_players_balance_paw")
    _drop_check("ledger", "ck_ledger_balance_after")

    op.create_table(
        "social_memberships",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("target_key", sa.String(length=16), nullable=False),
        sa.Column("is_member", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("reward_amount", sa.BigInteger(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "chat_id", name="uq_social_memberships_player_chat"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_social_memberships_chat_member",
        "social_memberships",
        ["chat_id", "is_member"],
    )


def downgrade() -> None:
    op.drop_index("ix_social_memberships_chat_member", table_name="social_memberships")
    op.drop_table("social_memberships")
    # Downgrade is intentionally not restoring non-negative constraints: a live database
    # may already contain legitimate negative PawCoin balances from this feature.
