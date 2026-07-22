"""Retire duels and solo games; pay every cocktail solver.

Both games staked currency that the idle loop already prints faster than any pot could
matter, and the duel lobby additionally needed a second live player inside a ten-minute
window — impossible at this population. Neither was played: over the five days the ledger
covers there were 7 solo bets and not one duel that reached a stake. They are gone.

Three things happen here:

* `cocktail_solves` is created, and the winners already recorded in `cocktail_days` are
  backfilled into it. Without the backfill the arena achievement, which now counts solved
  cocktails, would reset the progress of the players who had actually been winning.
* `duel_moves` and `duel_bonus` item properties become `expedition_power`. Players paid
  PawCoins and dollars to forge those, so they are converted rather than dropped — at the
  bottom of the `expedition_power` range for the item's rarity, since the old flat values
  (1-10) mean nothing on a percentage scale. An item that already had `expedition_power`
  has the two merged instead, because (item_id, kind, species_id) is unique.
* `duels`, `solo_matches` and `solo_stats` are dropped.

Ledger rows are deliberately untouched. `solo_stake` and `solo_payout` entries stay
exactly where they are: `SUM(delta) == balance` is the invariant the whole economy is
audited by, and rewriting history to erase a retired feature would break it.

Revision ID: 20260722_0039
Revises: 20260721_0038
"""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260722_0039"
down_revision = "20260721_0038"
branch_labels = None
depends_on = None

# Bottom of the `expedition_power` range per rarity, from catalog.ITEM_PROPERTIES. The low
# end, not the middle: this is compensation for a property that no longer has a game to
# apply to, and it should not out-roll what an honest forge would have produced.
_EXPEDITION_POWER_FLOOR = {
    "common": 4,
    "rare": 8,
    "epic": 14,
    "mythical": 20,
    "legendary": 25,
}
_EXPEDITION_POWER_CAP = 60


def _has_table(name: str) -> bool:
    return name in set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table("cocktail_solves"):
        op.create_table(
            "cocktail_solves",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.BigInteger(), nullable=False),
            sa.Column("day", sa.Date(), nullable=False),
            sa.Column("attempts", sa.SmallInteger(), nullable=False),
            sa.Column("was_first", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("reward_paw", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("player_id", "day", name="uq_cocktail_solves_player_day"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_cocktail_solves_day", "cocktail_solves", ["day"])

        # Past winners were paid 150 🐾 each and were first by definition. `attempts` is not
        # recoverable — the round rows were overwritten on the next reset — so it is recorded
        # as the maximum, which is the honest reading of "we do not know".
        bind.execute(
            sa.text(
                "INSERT INTO cocktail_solves (player_id, day, attempts, was_first, reward_paw, created_at) "
                "SELECT winner_player_id, day, 10, 1, 150, :now FROM cocktail_days "
                "WHERE winner_player_id IS NOT NULL"
            ).bindparams(now=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0))
        )

    # ─── Convert the duel properties ──────────────────────────────────────────
    rows = bind.execute(
        sa.text(
            "SELECT p.id, p.item_id, p.value, i.rarity FROM item_properties p "
            "JOIN items i ON i.id = p.item_id "
            "WHERE p.kind IN ('duel_moves', 'duel_bonus')"
        )
    ).fetchall()

    for row in rows:
        converted = _EXPEDITION_POWER_FLOOR.get(row.rarity, 4)
        existing = bind.execute(
            sa.text(
                "SELECT id, value FROM item_properties "
                "WHERE item_id = :item_id AND kind = 'expedition_power' AND species_id IS NULL"
            ).bindparams(item_id=row.item_id)
        ).fetchone()

        if existing is None:
            bind.execute(
                sa.text(
                    "UPDATE item_properties SET kind = 'expedition_power', value = :value WHERE id = :id"
                ).bindparams(value=converted, id=row.id)
            )
        else:
            merged = min(_EXPEDITION_POWER_CAP, existing.value + converted)
            bind.execute(
                sa.text("UPDATE item_properties SET value = :value WHERE id = :id").bindparams(
                    value=merged, id=existing.id
                )
            )
            bind.execute(sa.text("DELETE FROM item_properties WHERE id = :id").bindparams(id=row.id))

    # ─── Drop the retired tables ──────────────────────────────────────────────
    for table in ("solo_matches", "solo_stats", "duels"):
        if _has_table(table):
            op.drop_table(table)


def downgrade() -> None:
    """Restores the schema, not the data.

    The dropped rows are gone for good, and the converted properties cannot be told apart
    from honestly rolled `expedition_power` afterwards. This exists so a rollback finds the
    tables it expects, not to undo the retirement.
    """
    if not _has_table("duels"):
        op.create_table(
            "duels",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
            sa.Column("kind", sa.String(length=16), nullable=False),
            sa.Column("stake_rub", sa.BigInteger(), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="rub"),
            sa.Column("creator_id", sa.BigInteger(), nullable=False),
            sa.Column("creator_joined", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("opponent_id", sa.BigInteger(), nullable=True),
            sa.Column("third_player_id", sa.BigInteger(), nullable=True),
            sa.Column("winner_id", sa.BigInteger(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
            sa.Column("creator_score", sa.Integer(), nullable=True),
            sa.Column("opponent_score", sa.Integer(), nullable=True),
            sa.Column("third_score", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["creator_id"], ["players.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )

    if not _has_table("solo_stats"):
        op.create_table(
            "solo_stats",
            sa.Column("player_id", sa.BigInteger(), nullable=False),
            sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("won_rub", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("lost_rub", sa.BigInteger(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("player_id"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )

    if not _has_table("solo_matches"):
        op.create_table(
            "solo_matches",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.BigInteger(), nullable=False),
            sa.Column("kind", sa.String(length=16), nullable=False),
            sa.Column("stake_rub", sa.BigInteger(), nullable=False),
            sa.Column("won", sa.Boolean(), nullable=False),
            sa.Column("rub_delta", sa.BigInteger(), nullable=False),
            sa.Column("player_score", sa.Integer(), nullable=False),
            sa.Column("ai_score", sa.Integer(), nullable=False),
            sa.Column("history", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("player_id", name="uq_solo_matches_player"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )

    if _has_table("cocktail_solves"):
        op.drop_index("ix_cocktail_solves_day", table_name="cocktail_solves")
        op.drop_table("cocktail_solves")
