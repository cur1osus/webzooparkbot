from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260425_0010"
down_revision = "20260425_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zoopark_bank_vault",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usd_balance", sa.BigInteger(), nullable=False, server_default="0"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.execute("INSERT INTO zoopark_bank_vault (id, usd_balance) VALUES (1, 0)")


def downgrade() -> None:
    op.drop_table("zoopark_bank_vault")
