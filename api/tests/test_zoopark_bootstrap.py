from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from api.app.db.tables import ZOOPARK_BOOTSTRAP_META_TABLE, ZOOPARK_USERS_TABLE


def _make_conn_mock(
    existing_tables: set[str] | None = None,
    column_sets: dict[str, set[str]] | None = None,
    completed_targets: set[str] | None = None,
    table_counts: dict[str, int] | None = None,
):
    """Return a mock SQLAlchemy connection that simulates bootstrap SQL queries."""
    existing_tables = existing_tables or set()
    column_sets = column_sets or {}
    completed_targets = set(completed_targets or [])
    table_counts = dict(table_counts or {})
    copy_columns: dict[str, tuple[str, ...]] = {}

    def _execute(stmt, params=None):
        params = params or {}
        sql = str(stmt) if not isinstance(stmt, str) else stmt

        result = MagicMock()
        result.fetchone.return_value = None
        result.fetchall.return_value = []
        result.scalar.return_value = 0

        if "information_schema.TABLES" in sql:
            t = params.get("t", "")
            result.fetchone.return_value = (1,) if t in existing_tables else None
        elif "COLUMN_NAME" in sql and "information_schema" in sql:
            t = params.get("t", "")
            cols = column_sets.get(t, set())
            result.fetchall.return_value = [(c,) for c in sorted(cols)]
        elif "DATA_TYPE" in sql and "information_schema" in sql:
            t = params.get("t", "")
            c = params.get("c", "")
            has_col = c in column_sets.get(t, set())
            result.fetchone.return_value = ("bigint",) if has_col else None
        elif str(ZOOPARK_BOOTSTRAP_META_TABLE) in sql and "target_table=:t" in sql:
            t = params.get("t", "")
            result.fetchone.return_value = (1,) if t in completed_targets else None
        elif "COUNT(*)" in sql:
            table = ""
            for keyword in [ZOOPARK_USERS_TABLE, ZOOPARK_BOOTSTRAP_META_TABLE]:
                if keyword in sql:
                    table = keyword
                    break
            result.scalar.return_value = table_counts.get(table, 0)
            result.fetchone.return_value = (table_counts.get(table, 0),)
        elif "INSERT INTO" in sql and ") SELECT " in sql:
            # Extract table and columns from copy INSERT
            rest = sql.split("INSERT INTO ", 1)[1]
            tbl, _, remainder = rest.partition(" (")
            cols_sql, _, _ = remainder.partition(") SELECT ")
            cols = tuple(c.strip() for c in cols_sql.split(", "))
            copy_columns[tbl.strip()] = cols
            table_counts[tbl.strip()] = max(1, table_counts.get(tbl.strip(), 0))
        elif "ON DUPLICATE KEY UPDATE copied_at=CURRENT_TIMESTAMP" in sql:
            t = params.get("t", "")
            completed_targets.add(t)

        return result

    conn = MagicMock()
    conn.execute.side_effect = _execute
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    conn._copy_columns = copy_columns
    conn._completed_targets = completed_targets
    return conn


class ZooParkBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = dict(sys.modules)

        fastapi = types.ModuleType("fastapi")
        fastapi.HTTPException = type("HTTPException", (Exception,), {})
        sys.modules["fastapi"] = fastapi

        for name in ["api.app.db.bootstrap", "api.app.db.connection"]:
            sys.modules.pop(name, None)

    def tearDown(self) -> None:
        sys.modules.clear()
        sys.modules.update(self._saved_modules)

    def test_init_schema_copies_user_profile_fields_on_first_namespaced_bootstrap(self) -> None:
        module = importlib.import_module("api.app.db.bootstrap")

        user_cols = {
            "id", "id_user", "nickname", "date_reg", "paw_coins", "rub", "usd",
            "sub_on_chat", "sub_on_channel", "bonus", "unity_id", "is_banned",
            "balance_seq", "data_version", "bonus_notify_msg_id", "profile_emoji", "last_income_at",
        }

        conn = _make_conn_mock(
            existing_tables={
                "users", ZOOPARK_USERS_TABLE,
                ZOOPARK_BOOTSTRAP_META_TABLE,
            },
            column_sets={
                "users": user_cols,
                ZOOPARK_USERS_TABLE: user_cols,
            },
        )

        with patch.object(module, "engine") as mock_engine, \
             patch.object(module, "Base") as mock_base, \
             patch.object(module, "SessionLocal") as mock_sl, \
             patch.object(module, "seed_catalogue", return_value=None):
            mock_engine.connect.return_value = conn
            mock_base.metadata.create_all.return_value = None
            mock_session = MagicMock()
            mock_sl.return_value.__enter__.return_value = mock_session
            mock_sl.return_value.__exit__.return_value = False
            module.init_schema()

        copied = conn._copy_columns
        self.assertIn(ZOOPARK_USERS_TABLE, copied)
        self.assertEqual(
            copied[ZOOPARK_USERS_TABLE],
            (
                "id", "id_user", "nickname", "date_reg", "paw_coins", "rub", "usd",
                "sub_on_chat", "sub_on_channel", "bonus", "unity_id", "is_banned",
                "balance_seq", "data_version", "bonus_notify_msg_id", "profile_emoji", "last_income_at",
            ),
        )

    def test_init_schema_does_not_recopy_completed_compat_table_when_target_becomes_empty(self) -> None:
        module = importlib.import_module("api.app.db.bootstrap")

        user_cols = {"id", "id_user", "nickname", "date_reg", "paw_coins", "rub", "usd", "sub_on_chat", "sub_on_channel", "bonus"}
        conn = _make_conn_mock(
            existing_tables={"users", ZOOPARK_USERS_TABLE, ZOOPARK_BOOTSTRAP_META_TABLE},
            column_sets={"users": user_cols, ZOOPARK_USERS_TABLE: user_cols},
            completed_targets={ZOOPARK_USERS_TABLE},
        )

        with patch.object(module, "engine") as mock_engine, \
             patch.object(module, "Base") as mock_base, \
             patch.object(module, "SessionLocal") as mock_sl, \
             patch.object(module, "seed_catalogue", return_value=None):
            mock_engine.connect.return_value = conn
            mock_base.metadata.create_all.return_value = None
            mock_session = MagicMock()
            mock_sl.return_value.__enter__.return_value = mock_session
            mock_sl.return_value.__exit__.return_value = False
            module.init_schema()

        self.assertNotIn(ZOOPARK_USERS_TABLE, conn._copy_columns)


if __name__ == "__main__":
    unittest.main()
