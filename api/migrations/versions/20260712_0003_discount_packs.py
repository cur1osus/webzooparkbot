"""Repurpose the retired `discount_species` item property into `discount_packs`.

Buying animals from the merchant is no longer the main way to get them (packs are), so the
per-species merchant discount became dead weight. It is replaced by a global discount on
pack prices. Existing rows are converted: an item could hold more than one `discount_species`
(merged from different species), so they are folded into one NULL-species `discount_packs`
row to satisfy `uq_item_properties_item_kind_species`. The kind's CHECK domain is rewritten.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0003"
down_revision = "20260711_0002"
branch_labels = None
depends_on = None

_NEW_KINDS = (
    "income_total", "income_species", "discount_packs", "discount_locality",
    "discount_bank", "duel_moves", "duel_bonus", "bonus_rerolls",
)
_OLD_KINDS = (
    "income_total", "income_species", "discount_species", "discount_locality",
    "discount_bank", "duel_moves", "duel_bonus", "bonus_rerolls",
)


def _kind_in(kinds: tuple[str, ...]) -> str:
    return "kind IN (" + ", ".join(f"'{k}'" for k in kinds) + ")"


def upgrade() -> None:
    conn = op.get_bind()
    # Relax the domain so the retired kind can be rewritten.
    with op.batch_alter_table("item_properties") as batch_op:
        batch_op.drop_constraint("ck_item_properties_kind", type_="check")

    rows = conn.execute(
        sa.text(
            "SELECT item_id, SUM(value) AS total FROM item_properties "
            "WHERE kind = 'discount_species' GROUP BY item_id"
        )
    ).fetchall()
    conn.execute(sa.text("DELETE FROM item_properties WHERE kind = 'discount_species'"))
    insert = sa.text(
        "INSERT INTO item_properties (item_id, kind, value, species_id) "
        "VALUES (:item_id, 'discount_packs', :value, NULL)"
    )
    for item_id, total in rows:
        conn.execute(insert, {"item_id": int(item_id), "value": int(total)})

    with op.batch_alter_table("item_properties") as batch_op:
        batch_op.create_check_constraint("ck_item_properties_kind", _kind_in(_NEW_KINDS))


def downgrade() -> None:
    # The per-species split is lost when folding into a global discount, so this only restores
    # the kind name (species_id stays NULL) and the old CHECK domain.
    with op.batch_alter_table("item_properties") as batch_op:
        batch_op.drop_constraint("ck_item_properties_kind", type_="check")
    op.get_bind().execute(
        sa.text("UPDATE item_properties SET kind = 'discount_species' WHERE kind = 'discount_packs'")
    )
    with op.batch_alter_table("item_properties") as batch_op:
        batch_op.create_check_constraint("ck_item_properties_kind", _kind_in(_OLD_KINDS))
