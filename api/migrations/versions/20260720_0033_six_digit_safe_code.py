"""Retire safe rounds whose code is not the configured length.

`SAFE_CODE_LENGTH` went from 4 to 6. A live round still holding a four-digit secret would
be unwinnable: `safe_guess` rejects anything that is not six digits, so no guess could ever
match it. The round on production has no attempts against it yet, so dropping it loses
nothing; its attempts would cascade anyway.

The length is hardcoded here rather than imported from `catalog`: a migration records what
happened on the day it ran, and must not change meaning if the constant moves again.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260720_0033"
down_revision = "20260720_0032"
branch_labels = None
depends_on = None

CODE_LENGTH = 6


def upgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM safe_rounds WHERE solved_at IS NULL AND LENGTH(secret) <> :length"
        ).bindparams(length=CODE_LENGTH)
    )


def downgrade() -> None:
    # A deleted round cannot be restored, and recreating one would invent a code nobody
    # has seen. Solved rounds were never touched, so there is nothing to undo.
    pass
