from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from api.app.zoopark import income as income_module
from api.app.zoopark.db_tables import ZOOPARK_USERS_TABLE


UTC = timezone.utc


class _FakeCursor:
    def __init__(self, row: dict | None) -> None:
        self._row = row
        self.calls: list[tuple[str, tuple]] = []
        self.fetchone_queue: list[dict | None] = []

    def execute(self, sql: str, params: tuple) -> None:
        self.calls.append((sql, params))

    def fetchone(self):
        if self.fetchone_queue:
            return self.fetchone_queue.pop(0)
        return self._row


class _FixedDateTime:
    current = datetime(2026, 4, 18, 12, 0, tzinfo=UTC)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.current.replace(tzinfo=None)
        return cls.current.astimezone(tz)


class ZooParkIncomeTests(unittest.TestCase):
    def test_calc_legacy_income_applies_diversity_bonus(self) -> None:
        cursor = _FakeCursor({"base_income": 1000, "species_count": 3})

        result = income_module.calc_legacy_income(cursor, user_id=7)

        self.assertEqual(result, 1030)

    def test_accrue_income_uses_net_income(self) -> None:
        cursor = _FakeCursor({"last_income_at": _FixedDateTime.current - timedelta(minutes=2), "balance_seq": 0})
        user = {"id": 1, "rub": 100}

        with patch.object(income_module, "datetime", _FixedDateTime):
            result = income_module.accrue_income(cursor, user, income_rub_per_min=120, expenses_rub_per_min=30)

        self.assertEqual(result["rub"], 280)
        self.assertIn((f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (280, 1)), cursor.calls)

    def test_accrue_income_never_drops_below_zero(self) -> None:
        cursor = _FakeCursor({"last_income_at": _FixedDateTime.current - timedelta(minutes=1), "balance_seq": 0})
        user = {"id": 2, "rub": 50}

        with patch.object(income_module, "datetime", _FixedDateTime):
            result = income_module.accrue_income(cursor, user, income_rub_per_min=0, expenses_rub_per_min=120)

        self.assertEqual(result["rub"], 0)
        self.assertIn((f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (0, 2)), cursor.calls)

    def test_sync_passive_balance_uses_legacy_and_pack_income(self) -> None:
        cursor = _FakeCursor(None)
        cursor.fetchone_queue = [{"last_income_at": _FixedDateTime.current - timedelta(minutes=2), "balance_seq": 0}]
        user = {"id": 3, "rub": 100}

        with patch.object(income_module, "datetime", _FixedDateTime), \
             patch.object(income_module, "calc_legacy_income", return_value=100), \
             patch.object(income_module, "calc_pack_income", return_value=50), \
             patch.object(income_module, "calc_sick_expenses", return_value=10):
            updated_user, income_rub_per_min, expenses_rub_per_min = income_module.sync_passive_balance(cursor, user)

        self.assertEqual(income_rub_per_min, 150)
        self.assertEqual(expenses_rub_per_min, 10)
        self.assertEqual(updated_user["rub"], 380)
        self.assertIn((f"UPDATE {ZOOPARK_USERS_TABLE} SET rub=%s WHERE id=%s", (380, 3)), cursor.calls)


if __name__ == "__main__":
    unittest.main()
