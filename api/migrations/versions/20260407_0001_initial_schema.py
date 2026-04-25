from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import text

try:
    from alembic import op
except Exception:  # pragma: no cover - keeps helper unit tests importable without Alembic.
    op = SimpleNamespace(get_bind=lambda: None)


revision = "20260407_0001"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        text("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:table LIMIT 1"),
        {"table": table},
    )
    return result.fetchone() is not None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        text("SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:table AND COLUMN_NAME=:column LIMIT 1"),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def _index_exists(table: str, index: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        text("SELECT 1 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:table AND INDEX_NAME=:index LIMIT 1"),
        {"table": table, "index": index},
    )
    return result.fetchone() is not None


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    if not _table_exists(table) or _column_exists(table, column):
        return
    op.get_bind().execute(text(f"ALTER TABLE `{table}` ADD COLUMN {column} {definition}"))


def _add_index_if_missing(table: str, index: str, statement: str) -> None:
    if not _table_exists(table) or _index_exists(table, index):
        return
    op.get_bind().execute(text(statement))


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
