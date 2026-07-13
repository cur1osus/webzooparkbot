"""Allow rare daily animal and locality rewards."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260713_0017"
down_revision = "20260713_0016"
branch_labels = None
depends_on = None

DAILY_BONUS_KINDS = "'rub', 'usd', 'paw', 'locality', 'animal'"
ANIMAL_ORIGINS = "'pack', 'merchant', 'breeding', 'expedition', 'daily_bonus'"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("daily_bonuses", recreate="always") as batch:
            batch.add_column(sa.Column("reward_code", sa.String(length=32), nullable=True))
            batch.drop_constraint("ck_daily_bonuses_currency", type_="check")
            batch.create_check_constraint(
                "ck_daily_bonuses_currency",
                f"currency IN ({DAILY_BONUS_KINDS})",
            )
        with op.batch_alter_table("animals", recreate="always") as batch:
            batch.drop_constraint("ck_animals_origin", type_="check")
            batch.create_check_constraint("ck_animals_origin", f"origin IN ({ANIMAL_ORIGINS})")
        return

    op.add_column("daily_bonuses", sa.Column("reward_code", sa.String(length=32), nullable=True))
    op.drop_constraint("ck_daily_bonuses_currency", "daily_bonuses", type_="check")
    op.create_check_constraint(
        "ck_daily_bonuses_currency",
        "daily_bonuses",
        f"currency IN ({DAILY_BONUS_KINDS})",
    )
    op.drop_constraint("ck_animals_origin", "animals", type_="check")
    op.create_check_constraint("ck_animals_origin", "animals", f"origin IN ({ANIMAL_ORIGINS})")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("animals", recreate="always") as batch:
            batch.drop_constraint("ck_animals_origin", type_="check")
            batch.create_check_constraint(
                "ck_animals_origin",
                "origin IN ('pack', 'merchant', 'breeding', 'expedition')",
            )
        with op.batch_alter_table("daily_bonuses", recreate="always") as batch:
            batch.drop_column("reward_code")
            batch.drop_constraint("ck_daily_bonuses_currency", type_="check")
            batch.create_check_constraint(
                "ck_daily_bonuses_currency",
                "currency IN ('rub', 'usd', 'paw')",
            )
        return

    op.drop_constraint("ck_animals_origin", "animals", type_="check")
    op.create_check_constraint(
        "ck_animals_origin",
        "animals",
        "origin IN ('pack', 'merchant', 'breeding', 'expedition')",
    )
    op.drop_constraint("ck_daily_bonuses_currency", "daily_bonuses", type_="check")
    op.create_check_constraint(
        "ck_daily_bonuses_currency",
        "daily_bonuses",
        "currency IN ('rub', 'usd', 'paw')",
    )
    op.drop_column("daily_bonuses", "reward_code")
