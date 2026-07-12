"""Add locality infrastructure and player development tracks."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0008"
down_revision = "20260712_0007"
branch_labels = None
depends_on = None


_PROPERTY_KINDS = (
    "income_total", "income_species", "discount_upkeep", "discount_packs",
    "discount_locality", "discount_bank", "duel_moves", "duel_bonus", "bonus_rerolls",
)


def _kind_check() -> str:
    return "kind IN (" + ", ".join(f"'{kind}'" for kind in _PROPERTY_KINDS) + ")"


def upgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.add_column(sa.Column("vet_level", sa.SmallInteger(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("genetics_level", sa.SmallInteger(), nullable=False, server_default="0"))
        batch_op.create_check_constraint("ck_players_vet_level", "vet_level BETWEEN 0 AND 3")
        batch_op.create_check_constraint("ck_players_genetics_level", "genetics_level BETWEEN 0 AND 3")

    with op.batch_alter_table("localities") as batch_op:
        batch_op.add_column(sa.Column("level", sa.SmallInteger(), nullable=False, server_default="0"))
        batch_op.create_check_constraint("ck_localities_level", "level BETWEEN 0 AND 3")

    with op.batch_alter_table("item_properties") as batch_op:
        batch_op.drop_constraint("ck_item_properties_kind", type_="check")
        batch_op.create_check_constraint("ck_item_properties_kind", _kind_check())


def downgrade() -> None:
    with op.batch_alter_table("item_properties") as batch_op:
        batch_op.drop_constraint("ck_item_properties_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_item_properties_kind",
            "kind IN ('income_total', 'income_species', 'discount_packs', 'discount_locality',"
            " 'discount_bank', 'duel_moves', 'duel_bonus', 'bonus_rerolls')",
        )

    with op.batch_alter_table("localities") as batch_op:
        batch_op.drop_constraint("ck_localities_level", type_="check")
        batch_op.drop_column("level")
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_constraint("ck_players_genetics_level", type_="check")
        batch_op.drop_constraint("ck_players_vet_level", type_="check")
        batch_op.drop_column("genetics_level")
        batch_op.drop_column("vet_level")
