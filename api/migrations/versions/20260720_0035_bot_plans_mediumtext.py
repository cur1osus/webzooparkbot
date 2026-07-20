"""Widen `bot_plans.tool_calls` past MySQL's TEXT ceiling.

A rival's turn is journalled as the full list of tool calls and their results. Once its zoo
had grown, a single turn serialised past the 64 KiB a MySQL TEXT column holds, and the
insert began failing with error 1406. SQLite's TEXT has no such limit, so nothing caught it
before production.

The runner now clips each result before storing it, which keeps the journal readable and
well under any ceiling. This migration is the backstop underneath that: a turn that is long
rather than verbose should still be recorded rather than lost.

Only MySQL is altered — on SQLite the column is already unbounded, and `ALTER COLUMN` there
would mean rebuilding the table for no change at all.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

revision = "20260720_0035"
down_revision = "20260720_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    op.alter_column("bot_plans", "tool_calls", type_=MEDIUMTEXT(), existing_nullable=False)


def downgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    # Narrowing truncates any row that has since grown past 64 KiB. That is inherent to
    # going back, and the journal is history rather than game state.
    op.alter_column("bot_plans", "tool_calls", type_=sa.Text(), existing_nullable=False)
