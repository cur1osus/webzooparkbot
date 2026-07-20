"""Let the outbox address a chat, and give up on permanently undeliverable messages."""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from alembic import op


revision = "20260720_0031"
down_revision = "20260720_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("notification_outbox") as batch:
        batch.add_column(sa.Column("chat_id", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("failed_at", sa.DateTime(), nullable=True))
        # A broadcast row has no player at all, so the column can no longer be required.
        batch.alter_column("player_id", existing_type=sa.BigInteger(), nullable=True)

    # Rows already in flight all address a player, so the constraint holds for them.
    if bind.dialect.name != "sqlite":
        op.create_check_constraint(
            "ck_notification_outbox_recipient",
            "notification_outbox",
            "(player_id IS NULL) <> (chat_id IS NULL)",
        )

    # The 42 rows stuck retrying a chat that will never exist: settle them once here rather
    # than waiting for each to fail one last time. Only the kinds that were observed
    # failing, and only ones already given up on by the backoff (many attempts).
    # `NOW()` is MySQL-only and the test suite migrates SQLite; the timestamp is bound from
    # Python as naive UTC, which is exactly what `UtcDateTime` stores.
    op.execute(
        sa.text(
            "UPDATE notification_outbox SET failed_at = :now, last_error = 'постоянный отказ Bot API' "
            "WHERE sent_at IS NULL AND failed_at IS NULL AND attempts >= 5 AND last_error IS NOT NULL"
        ).bindparams(now=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("ck_notification_outbox_recipient", "notification_outbox", type_="check")
    with op.batch_alter_table("notification_outbox") as batch:
        batch.drop_column("failed_at")
        batch.drop_column("chat_id")
