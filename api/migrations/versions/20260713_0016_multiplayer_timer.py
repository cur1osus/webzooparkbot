"""Turn duels into timed three-player multiplayer lobbies."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260713_0016"
down_revision = "20260713_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Legacy open duels charged the creator on creation, so old rows are treated as
    # already joined. New rows explicitly write False until the owner presses Join.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite cannot add a foreign-key constraint with ALTER TABLE, but the ORM and
        # runtime still enforce the relationship. Keeping this as native ADD COLUMN also
        # preserves the original INTEGER PRIMARY KEY autoincrement on the test database.
        bind.execute(sa.text("ALTER TABLE duels ADD COLUMN creator_joined BOOLEAN NOT NULL DEFAULT 1"))
        bind.execute(sa.text("ALTER TABLE duels ADD COLUMN third_player_id BIGINT"))
        bind.execute(sa.text("ALTER TABLE duels ADD COLUMN third_score INTEGER"))
        bind.execute(sa.text("ALTER TABLE duels ADD COLUMN expires_at DATETIME"))
    else:
        op.add_column("duels", sa.Column("creator_joined", sa.Boolean(), nullable=False, server_default=sa.true()))
        op.add_column(
            "duels",
            sa.Column("third_player_id", sa.BigInteger(), sa.ForeignKey("players.id", name="fk_duels_third_player_id_players", ondelete="SET NULL"), nullable=True),
        )
        op.add_column("duels", sa.Column("third_score", sa.Integer(), nullable=True))
        op.add_column("duels", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.create_index("ix_duels_expires", "duels", ["status", "expires_at"])


def downgrade() -> None:
    op.drop_index("ix_duels_expires", table_name="duels")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("duels", recreate="always") as batch:
            batch.drop_column("expires_at")
            batch.drop_column("third_score")
            batch.drop_column("third_player_id")
            batch.drop_column("creator_joined")
    else:
        op.drop_column("duels", "expires_at")
        op.drop_column("duels", "third_score")
        op.drop_column("duels", "third_player_id")
        op.drop_column("duels", "creator_joined")
