"""Add web credentials and sessions for non-Telegram access

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-07
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, column: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": table, "c": column}).fetchone()
    return (row[0] if row else 0) > 0


def _has_table(conn, table: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) as cnt FROM information_schema.TABLES"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {"t": table}).fetchone()
    return (row[0] if row else 0) > 0


def _has_index(conn, table: str, index_name: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) as cnt FROM information_schema.STATISTICS"
        " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND INDEX_NAME = :i"
    ), {"t": table, "i": index_name}).fetchone()
    return (row[0] if row else 0) > 0


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "mysql":
        return

    if not _has_table(conn, "users"):
        return

    if not _has_column(conn, "users", "web_login"):
        conn.execute(text("ALTER TABLE `users` ADD COLUMN web_login VARCHAR(64) NULL DEFAULT NULL"))

    if not _has_column(conn, "users", "web_password_hash"):
        conn.execute(text("ALTER TABLE `users` ADD COLUMN web_password_hash VARCHAR(256) NULL DEFAULT NULL"))

    if not _has_index(conn, "users", "uq_web_login"):
        conn.execute(text("ALTER TABLE users ADD UNIQUE KEY uq_web_login (web_login)"))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS web_sessions (
            token      VARCHAR(64)  NOT NULL PRIMARY KEY,
            tg_id      BIGINT       NOT NULL,
            created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_tg_id (tg_id)
        )
    """))


def downgrade() -> None:
    pass
