"""Store deterministic outcome metrics for each bot turn.

The raw journal remains the audit trail.  This separate MEDIUMTEXT column stores the compact
state deltas and counters needed for comparing turns and models without replaying that journal.

Revision ID: 20260728_0041
Revises: 20260722_0040
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

revision = "20260728_0041"
down_revision = "20260722_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    column_type = sa.Text().with_variant(MEDIUMTEXT(), "mysql")
    op.add_column("bot_plans", sa.Column("evaluation", column_type, nullable=True))
    op.execute(sa.text("UPDATE bot_plans SET evaluation = '{}' WHERE evaluation IS NULL"))
    # Batch mode keeps the migration runnable against the SQLite database used by the
    # migration-shape test; MySQL receives the equivalent ALTER operation.
    with op.batch_alter_table("bot_plans") as batch_op:
        batch_op.alter_column("evaluation", existing_type=column_type, nullable=False)


def downgrade() -> None:
    op.drop_column("bot_plans", "evaluation")
