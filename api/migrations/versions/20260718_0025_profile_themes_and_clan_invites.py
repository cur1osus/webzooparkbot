"""Add server-owned profile themes and invitation-only clans."""

from __future__ import annotations

import secrets

import sqlalchemy as sa
from alembic import op


revision = "20260718_0025"
down_revision = "20260717_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.add_column(sa.Column("theme", sa.String(length=16), nullable=False, server_default="dusk"))

    with op.batch_alter_table("clans") as batch_op:
        batch_op.add_column(sa.Column("invite_code", sa.String(length=24), nullable=True))

    # Existing clans need a stable invite token before the column can become required.
    bind = op.get_bind()
    clans = sa.table("clans", sa.column("id", sa.BigInteger()), sa.column("invite_code", sa.String(24)))
    rows = bind.execute(sa.select(clans.c.id)).all()
    for (clan_id,) in rows:
        bind.execute(
            clans.update().where(clans.c.id == clan_id).values(invite_code=f"legacy-{clan_id}-{secrets.token_hex(5)}")
        )

    with op.batch_alter_table("clans") as batch_op:
        batch_op.alter_column("invite_code", existing_type=sa.String(length=24), nullable=False)
        batch_op.create_unique_constraint("uq_clans_invite_code", ["invite_code"])


def downgrade() -> None:
    with op.batch_alter_table("clans") as batch_op:
        batch_op.drop_constraint("uq_clans_invite_code", type_="unique")
        batch_op.drop_column("invite_code")
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_column("theme")
