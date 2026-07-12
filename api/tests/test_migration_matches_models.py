"""The migration and the ORM must describe the same database.

`models.py` is the source of truth for the code; the revision is the source of truth for
the database. Nothing keeps them honest except this test — Alembic autogenerate is off
(`target_metadata = None`), because the schema is written by hand.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from api.app.db.models import Base

API_DIR = Path(__file__).resolve().parents[1]

# SQLite has no unsigned/engine/charset notions and renders CHECK constraints differently,
# so this compares the shape both dialects agree on: which tables exist, and which columns
# each one has. A column added to one side and not the other is the drift that bites.
IGNORED_TABLES = {"alembic_version", "sqlite_sequence"}


@pytest.fixture(scope="module")
def migrated_engine(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("alembic") / "migrated.db"
    url = f"sqlite:///{db_path}"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_DIR,
        env={"PATH": "/usr/bin:/bin", "DB_URL": url, "HOME": str(db_path.parent)},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}")

    return create_engine(url)


def _migrated_tables(engine) -> dict[str, set[str]]:
    inspector = inspect(engine)
    return {
        name: {column["name"] for column in inspector.get_columns(name)}
        for name in inspector.get_table_names()
        if name not in IGNORED_TABLES
    }


def _orm_tables() -> dict[str, set[str]]:
    return {name: set(table.columns.keys()) for name, table in Base.metadata.tables.items()}


def test_the_migration_creates_every_table_the_orm_declares(migrated_engine):
    migrated = _migrated_tables(migrated_engine)
    orm = _orm_tables()

    assert set(migrated) == set(orm), (
        f"only in the migration: {sorted(set(migrated) - set(orm))}; "
        f"only in models.py: {sorted(set(orm) - set(migrated))}"
    )


def test_every_table_has_the_columns_the_orm_declares(migrated_engine):
    migrated = _migrated_tables(migrated_engine)
    orm = _orm_tables()

    drift = {
        table: {
            "only_in_migration": sorted(migrated[table] - orm[table]),
            "only_in_models": sorted(orm[table] - migrated[table]),
        }
        for table in sorted(set(migrated) & set(orm))
        if migrated[table] != orm[table]
    }
    assert not drift, f"the migration and models.py disagree: {drift}"
