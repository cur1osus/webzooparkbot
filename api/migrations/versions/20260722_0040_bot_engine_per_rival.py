"""Give each rival its own engine, and record which one played each turn.

The model was a deployment-wide setting, which made the only question worth asking about it
unanswerable. Comparing two engines meant switching the variable and waiting, and by then the
zoo had moved: a rival that has bought its fifth and last locality grows by what the packs
happen to drop, not by how well it thinks, so the "after" was never the same experiment as
the "before".

So `bot_profiles.model` is nullable and NULL keeps today's behaviour — the deployment default
— while a second rival can be pointed at something else and run beside the first on the same
game and the same clock.

`bot_plans.model` is the other half, and the more important one. Without it the journal has
no memory of which engine produced a turn: the rows before and after a swap are identical,
and the only record is whatever the operator recalls about when they changed the setting.
Existing turns backfill to the model that was configured when they were played.

Revision ID: 20260722_0040
Revises: 20260722_0039
"""

from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op

# Read from the environment rather than imported from `api.app.core.config`: migrations run
# under a bare alembic where the package is not importable, and the test that applies them
# from zero fails on the import alone. Same variable, same default.
BOT_PLANNER_MODEL = os.getenv("BOT_PLANNER_MODEL", "deepseek/deepseek-v4-flash")

revision = "20260722_0040"
down_revision = "20260722_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bot_profiles", sa.Column("model", sa.String(64), nullable=True))
    op.add_column(
        "bot_plans",
        sa.Column("model", sa.String(64), nullable=False, server_default=""),
    )
    # Every turn in the journal was played by whatever was configured at the time, and the
    # only thing that ever set it is this variable. Leaving them blank would read as "unknown"
    # for turns that are in fact the baseline the first comparison is measured against.
    op.execute(
        sa.text("UPDATE bot_plans SET model = :model WHERE model = ''").bindparams(
            model=BOT_PLANNER_MODEL
        )
    )


def downgrade() -> None:
    op.drop_column("bot_plans", "model")
    op.drop_column("bot_profiles", "model")
