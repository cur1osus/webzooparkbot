from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "20260415_0008_more_features.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("migration_0008_more_features", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Migration0008Tests(unittest.TestCase):
    def test_upgrade_skips_existing_tables(self) -> None:
        module = _load_module()

        with patch.object(module, "_table_exists", return_value=True), \
             patch.object(module.op, "create_table") as create_table:
            module.upgrade()

        create_table.assert_not_called()


if __name__ == "__main__":
    unittest.main()
