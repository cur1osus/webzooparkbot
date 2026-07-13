"""Persist cocktail boards and make the daily reward global."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260714_0017"
down_revision = "20260713_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(sa.text("ALTER TABLE cocktail_rounds ADD COLUMN history TEXT NOT NULL DEFAULT '[]'"))
    else:
        # MySQL rejects defaults on TEXT columns. Add it nullable, backfill existing
        # rounds, then enforce the ORM's non-null contract without a server default.
        op.add_column("cocktail_rounds", sa.Column("history", sa.Text(), nullable=True))
        bind.execute(sa.text("UPDATE cocktail_rounds SET history = '[]' WHERE history IS NULL"))
        op.alter_column("cocktail_rounds", "history", existing_type=sa.Text(), nullable=False)

    op.create_table(
        "cocktail_days",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("winner_player_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["winner_player_id"], ["players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("day"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )


def downgrade() -> None:
    op.drop_table("cocktail_days")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("cocktail_rounds", recreate="always") as batch:
            batch.drop_column("history")
    else:
        op.drop_column("cocktail_rounds", "history")
