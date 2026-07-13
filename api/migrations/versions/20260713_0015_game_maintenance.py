"""Add the singleton technical-break timer."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


revision = "20260713_0015"
down_revision = "20260713_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_maintenance",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("message", sa.String(length=160), nullable=False, server_default="Технический перерыв"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.get_bind().execute(
        sa.text(
            "INSERT INTO game_maintenance (id, message, updated_at) "
            "VALUES (1, 'Технический перерыв', :updated_at)"
        ),
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None)},
    )


def downgrade() -> None:
    op.drop_table("game_maintenance")
