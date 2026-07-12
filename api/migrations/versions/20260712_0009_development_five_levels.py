"""Expand development tracks and locality infrastructure to five levels."""

from __future__ import annotations

from alembic import op

revision = "20260712_0009"
down_revision = "20260712_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_constraint("ck_players_vet_level", type_="check")
        batch_op.drop_constraint("ck_players_genetics_level", type_="check")
        batch_op.create_check_constraint("ck_players_vet_level", "vet_level BETWEEN 0 AND 5")
        batch_op.create_check_constraint("ck_players_genetics_level", "genetics_level BETWEEN 0 AND 5")

    with op.batch_alter_table("localities") as batch_op:
        batch_op.drop_constraint("ck_localities_level", type_="check")
        batch_op.create_check_constraint("ck_localities_level", "level BETWEEN 0 AND 5")


def downgrade() -> None:
    with op.batch_alter_table("localities") as batch_op:
        batch_op.drop_constraint("ck_localities_level", type_="check")
        batch_op.create_check_constraint("ck_localities_level", "level BETWEEN 0 AND 3")

    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_constraint("ck_players_genetics_level", type_="check")
        batch_op.drop_constraint("ck_players_vet_level", type_="check")
        batch_op.create_check_constraint("ck_players_vet_level", "vet_level BETWEEN 0 AND 3")
        batch_op.create_check_constraint("ck_players_genetics_level", "genetics_level BETWEEN 0 AND 3")
