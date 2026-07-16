"""Expedition depth, the corps track, and one expedition per locality.

Revision ID: 20260716_0021
Revises: 20260714_0020
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260716_0021"
down_revision = "20260714_0020"
branch_labels = None
depends_on = None


# Spelled out rather than imported from the catalogue: a migration describes the database as
# it was at this revision, and must not drift when the catalogue's tuple changes later.
_PROPERTY_KINDS_BEFORE = (
    "income_total", "income_species", "discount_upkeep", "discount_packs",
    "discount_locality", "discount_bank", "duel_moves", "duel_bonus", "bonus_rerolls",
)
_PROPERTY_KINDS_AFTER = _PROPERTY_KINDS_BEFORE + ("expedition_power",)


def _kind_check(kinds: tuple[str, ...]) -> str:
    return "kind IN (" + ", ".join(f"'{kind}'" for kind in kinds) + ")"


def _alters_constraints() -> bool:
    """Whether this backend can ALTER a constraint on `expeditions`.

    The app runs on MySQL, which can. SQLite cannot ALTER constraints at all, and Alembic's
    batch fallback — copy the table, move it back — cannot reproduce `active_marker`, a
    stored generated column it is not allowed to INSERT into. SQLite reaches this migration
    only from `test_migration_matches_models`, which compares which tables and columns exist
    and never inspects a constraint, so skipping the constraint DDL there costs that test
    nothing and keeps the real (MySQL) path free of a copy-and-move on a live table.
    """
    return op.get_bind().dialect.name != "sqlite"


def _has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in inspect(op.get_bind()).get_columns(table)}


def _check_constraint(table: str, name: str) -> dict | None:
    return next(
        (item for item in inspect(op.get_bind()).get_check_constraints(table) if item.get("name") == name),
        None,
    )


def _has_unique_constraint(table: str, name: str) -> bool:
    return any(item.get("name") == name for item in inspect(op.get_bind()).get_unique_constraints(table))


def upgrade() -> None:
    # Depth 1 is exactly the balance that shipped before depth existed — the habitat's own
    # gene and rarity tables, unshifted — so every in-flight expedition keeps its odds.
    # Plain ADD COLUMN, which both backends support, precisely to avoid batch mode here.
    if not _has_column("expeditions", "depth"):
        op.add_column("expeditions", sa.Column("depth", sa.SmallInteger(), nullable=False, server_default="1"))

    with op.batch_alter_table("players") as batch_op:
        if not _has_column("players", "expedition_level"):
            batch_op.add_column(
                sa.Column("expedition_level", sa.SmallInteger(), nullable=False, server_default="0")
            )
        if _check_constraint("players", "ck_players_expedition_level") is None:
            batch_op.create_check_constraint("ck_players_expedition_level", "expedition_level BETWEEN 0 AND 5")

    # The forge's half of the expedition power axis needs a home in the kind whitelist.
    item_kind_check = _check_constraint("item_properties", "ck_item_properties_kind")
    if item_kind_check is None or "expedition_power" not in (item_kind_check.get("sqltext") or ""):
        with op.batch_alter_table("item_properties") as batch_op:
            if item_kind_check is not None:
                batch_op.drop_constraint("ck_item_properties_kind", type_="check")
            batch_op.create_check_constraint("ck_item_properties_kind", _kind_check(_PROPERTY_KINDS_AFTER))

    if not _alters_constraints():
        return

    if _check_constraint("expeditions", "ck_expeditions_depth") is None:
        op.create_check_constraint("ck_expeditions_depth", "expeditions", "depth BETWEEN 1 AND 5")
    # Widen the "one active expedition" rule from the whole zoo to a single locality, so a
    # player can run one raid per locality they own.
    if not _has_unique_constraint("expeditions", "uq_expeditions_one_active_per_locality"):
        # Create the replacement first: MySQL may use the old unique key as the required
        # index for the expeditions.player_id foreign key until another index exists.
        op.create_unique_constraint(
            "uq_expeditions_one_active_per_locality",
            "expeditions",
            ["player_id", "season_id", "locality_id", "active_marker"],
        )
    if _has_unique_constraint("expeditions", "uq_expeditions_one_active"):
        op.drop_constraint("uq_expeditions_one_active", "expeditions", type_="unique")


def downgrade() -> None:
    if _alters_constraints():
        # Reinstating the zoo-wide unique key fails where a player legitimately has several
        # raids in flight, so resolve every unresolved expedition first. `active_marker` is a
        # generated column and follows `resolved_at` on its own.
        op.execute("UPDATE expeditions SET resolved_at = ends_at WHERE resolved_at IS NULL")
        op.drop_constraint("uq_expeditions_one_active_per_locality", "expeditions", type_="unique")
        op.create_unique_constraint(
            "uq_expeditions_one_active", "expeditions", ["player_id", "season_id", "active_marker"]
        )
        op.drop_constraint("ck_expeditions_depth", "expeditions", type_="check")

    # Items carrying the property must go before the property leaves the whitelist.
    op.execute("DELETE FROM item_properties WHERE kind = 'expedition_power'")
    with op.batch_alter_table("item_properties") as batch_op:
        batch_op.drop_constraint("ck_item_properties_kind", type_="check")
        batch_op.create_check_constraint("ck_item_properties_kind", _kind_check(_PROPERTY_KINDS_BEFORE))

    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_constraint("ck_players_expedition_level", type_="check")
        batch_op.drop_column("expedition_level")

    op.drop_column("expeditions", "depth")
