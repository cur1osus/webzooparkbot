from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "20260407_0001_initial_schema.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("migration_0001_initial_schema", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Migration0001Tests(unittest.TestCase):
    def test_add_column_if_missing_executes_single_alter_statement(self) -> None:
        module = _load_module()
        conn = MagicMock()

        with patch.object(module.op, "get_bind", return_value=conn), \
             patch.object(module, "_table_exists", return_value=True), \
             patch.object(module, "_column_exists", return_value=False):
            module._add_column_if_missing("users", "balance_seq", "INT DEFAULT 0")

        executed = str(conn.execute.call_args.args[0])
        self.assertEqual(executed, "ALTER TABLE `users` ADD COLUMN balance_seq INT DEFAULT 0")

    def test_add_column_if_missing_is_noop_when_column_exists(self) -> None:
        module = _load_module()
        conn = MagicMock()

        with patch.object(module.op, "get_bind", return_value=conn), \
             patch.object(module, "_table_exists", return_value=True), \
             patch.object(module, "_column_exists", return_value=True):
            module._add_column_if_missing("users", "balance_seq", "INT DEFAULT 0")

        conn.execute.assert_not_called()

    def test_add_index_if_missing_executes_single_statement(self) -> None:
        module = _load_module()
        conn = MagicMock()

        with patch.object(module.op, "get_bind", return_value=conn), \
             patch.object(module, "_table_exists", return_value=True), \
             patch.object(module, "_index_exists", return_value=False):
            module._add_index_if_missing("aviaries", "uq_code_name", "ALTER TABLE aviaries ADD UNIQUE KEY uq_code_name (code_name)")

        executed = str(conn.execute.call_args.args[0])
        self.assertEqual(executed, "ALTER TABLE aviaries ADD UNIQUE KEY uq_code_name (code_name)")


if __name__ == "__main__":
    unittest.main()
