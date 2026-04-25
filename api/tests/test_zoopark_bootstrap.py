from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import patch

from api.app.db.tables import ZOOPARK_BOOTSTRAP_META_TABLE, ZOOPARK_EXTRA_TABLE, ZOOPARK_PACK_ANIMALS_TABLE


class _BootstrapCursor:
    def __init__(self) -> None:
        self.tables: dict[str, set[str]] = {
            "webapp_extra": {"user_id", "balance_seq", "data_version", "profile_emoji", "forge_sets_json", "packs_today", "packs_today_date", "last_income_at"},
            "pack_animals": {
                "id",
                "user_id",
                "survival",
                "reproduction",
                "appearance",
                "size_trait",
                "habitat",
                "is_alive",
                "acquired_at",
                "dies_at",
                "locality_id",
                "last_bred_date",
                "in_expedition",
            },
        }
        self.copy_columns: dict[str, tuple[str, ...]] = {}
        self.table_counts: dict[str, int] = {}
        self.completed_targets: set[str] = set()
        self._fetchone: dict | None = None
        self._fetchall: list[dict] = []

    def execute(self, sql: str, params: tuple | None = None) -> None:
        params = params or ()

        if sql.startswith("CREATE TABLE IF NOT EXISTS "):
            table, columns = self._parse_create_table(sql)
            self.tables[table] = columns
            self._fetchone = None
            self._fetchall = []
            return

        if sql.startswith("ALTER TABLE ") and " ADD COLUMN " in sql:
            table, column = self._parse_alter_add_column(sql)
            self.tables.setdefault(table, set()).add(column)
            self._fetchone = None
            self._fetchall = []
            return

        if sql.startswith("SELECT 1 FROM information_schema.TABLES"):
            table = str(params[0])
            self._fetchone = {"1": 1} if table in self.tables else None
            self._fetchall = []
            return

        if sql.startswith("SELECT COLUMN_NAME FROM information_schema.COLUMNS"):
            table = str(params[0])
            self._fetchone = None
            self._fetchall = [{"COLUMN_NAME": column} for column in sorted(self.tables.get(table, set()))]
            return

        if sql.startswith("SELECT DATA_TYPE FROM information_schema.COLUMNS"):
            table = str(params[0])
            column = str(params[1])
            self._fetchone = {"DATA_TYPE": "bigint"} if column in self.tables.get(table, set()) else None
            self._fetchall = []
            return

        if sql.startswith(f"SELECT 1 AS exists_flag FROM {ZOOPARK_BOOTSTRAP_META_TABLE} WHERE target_table=%s LIMIT 1"):
            target_table = str(params[0])
            self._fetchone = {"exists_flag": 1} if target_table in self.completed_targets else None
            self._fetchall = []
            return

        if sql.startswith("SELECT COUNT(*) AS cnt FROM "):
            table = sql.split("SELECT COUNT(*) AS cnt FROM ", 1)[1]
            self._fetchone = {"cnt": self.table_counts.get(table, 0)}
            self._fetchall = []
            return

        if sql.startswith(f"INSERT INTO {ZOOPARK_BOOTSTRAP_META_TABLE} (target_table) VALUES (%s) ON DUPLICATE KEY UPDATE copied_at=CURRENT_TIMESTAMP"):
            target_table = str(params[0])
            self.completed_targets.add(target_table)
            self.table_counts[ZOOPARK_BOOTSTRAP_META_TABLE] = len(self.completed_targets)
            self._fetchone = None
            self._fetchall = []
            return

        if sql.startswith("INSERT INTO ") and ") SELECT " in sql:
            table, columns = self._parse_copy_insert(sql)
            self.copy_columns[table] = columns
            self.table_counts[table] = max(1, self.table_counts.get(table, 0))
            self._fetchone = None
            self._fetchall = []
            return

        self._fetchone = None
        self._fetchall = []

    def fetchone(self):
        return self._fetchone

    def fetchall(self):
        return list(self._fetchall)

    @staticmethod
    def _parse_create_table(sql: str) -> tuple[str, set[str]]:
        table = sql.split("CREATE TABLE IF NOT EXISTS ", 1)[1].split(" ", 1)[0]
        body = sql.split("(", 1)[1].rsplit(")", 1)[0]
        columns: set[str] = set()
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line or line.startswith(("PRIMARY KEY", "INDEX", "UNIQUE KEY")):
                continue
            columns.add(line.split(" ", 1)[0].strip("`"))
        return table, columns

    @staticmethod
    def _parse_alter_add_column(sql: str) -> tuple[str, str]:
        parts = sql.split()
        return parts[2], parts[5]

    @staticmethod
    def _parse_copy_insert(sql: str) -> tuple[str, tuple[str, ...]]:
        rest = sql.split("INSERT INTO ", 1)[1]
        table, _, remainder = rest.partition(" (")
        columns_sql = remainder.split(") SELECT ", 1)[0]
        return table, tuple(column.strip() for column in columns_sql.split(", "))


class _BootstrapDb:
    def __init__(self, cursor: _BootstrapCursor) -> None:
        self._cursor = cursor

    def cursor(self):
        return self

    def __enter__(self):
        return self._cursor

    def __exit__(self, exc_type, exc, tb):
        return False

    def commit(self) -> None:
        return None

    def close(self) -> None:
        return None


class ZooParkBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = dict(sys.modules)

        fastapi = types.ModuleType("fastapi")
        fastapi.HTTPException = type("HTTPException", (Exception,), {})
        sys.modules["fastapi"] = fastapi

        pymysql = types.ModuleType("pymysql")
        pymysql.connect = lambda **_kwargs: None
        sys.modules["pymysql"] = pymysql

        pymysql_cursors = types.ModuleType("pymysql.cursors")
        pymysql_cursors.DictCursor = object
        sys.modules["pymysql.cursors"] = pymysql_cursors
        pymysql.cursors = pymysql_cursors

        for name in ["api.app.db.bootstrap", "api.app.db.connection"]:
            sys.modules.pop(name, None)

    def tearDown(self) -> None:
        sys.modules.clear()
        sys.modules.update(self._saved_modules)

    def test_init_schema_copies_optional_fields_on_first_namespaced_bootstrap(self) -> None:
        module = importlib.import_module("api.app.db.bootstrap")
        cursor = _BootstrapCursor()
        db = _BootstrapDb(cursor)

        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "seed_catalogue", return_value=None):
            module.init_schema()

        self.assertEqual(
            cursor.copy_columns[ZOOPARK_EXTRA_TABLE],
            ("user_id", "balance_seq", "data_version", "profile_emoji", "forge_sets_json", "packs_today", "packs_today_date", "last_income_at"),
        )
        self.assertEqual(
            cursor.copy_columns[ZOOPARK_PACK_ANIMALS_TABLE],
            (
                "id",
                "user_id",
                "survival",
                "reproduction",
                "appearance",
                "size_trait",
                "habitat",
                "is_alive",
                "acquired_at",
                "dies_at",
                "locality_id",
                "last_bred_date",
                "in_expedition",
            ),
        )

    def test_init_schema_does_not_recopy_completed_compat_table_when_target_becomes_empty(self) -> None:
        module = importlib.import_module("api.app.db.bootstrap")
        cursor = _BootstrapCursor()
        db = _BootstrapDb(cursor)

        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "seed_catalogue", return_value=None):
            module.init_schema()

        cursor.copy_columns = {}
        cursor.table_counts[ZOOPARK_EXTRA_TABLE] = 0
        cursor.table_counts[ZOOPARK_PACK_ANIMALS_TABLE] = 0

        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "seed_catalogue", return_value=None):
            module.init_schema()

        self.assertEqual(cursor.copy_columns, {})


if __name__ == "__main__":
    unittest.main()
