from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from api.app.zoopark import income as income_module


UTC = timezone.utc


class _FakeCursor:
    def __init__(self, row: dict | None) -> None:
        self._row = row
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple) -> None:
        self.calls.append((sql, params))

    def fetchone(self):
        return self._row


class _FixedDateTime:
    current = datetime(2026, 4, 18, 12, 0, tzinfo=UTC)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.current.replace(tzinfo=None)
        return cls.current.astimezone(tz)


class ZooParkIncomeTests(unittest.TestCase):
    def test_accrue_income_uses_net_income(self) -> None:
        cursor = _FakeCursor({"last_income_at": _FixedDateTime.current - timedelta(minutes=2), "balance_seq": 0})
        user = {"id": 1, "rub": 100}

        with patch.object(income_module, "datetime", _FixedDateTime):
            result = income_module.accrue_income(cursor, user, income_rub_per_min=120, expenses_rub_per_min=30)

        self.assertEqual(result["rub"], 280)
        self.assertIn(("UPDATE users SET rub=%s WHERE id=%s", (280, 1)), cursor.calls)

    def test_accrue_income_never_drops_below_zero(self) -> None:
        cursor = _FakeCursor({"last_income_at": _FixedDateTime.current - timedelta(minutes=1), "balance_seq": 0})
        user = {"id": 2, "rub": 50}

        with patch.object(income_module, "datetime", _FixedDateTime):
            result = income_module.accrue_income(cursor, user, income_rub_per_min=0, expenses_rub_per_min=120)

        self.assertEqual(result["rub"], 0)
        self.assertIn(("UPDATE users SET rub=%s WHERE id=%s", (0, 2)), cursor.calls)


if __name__ == "__main__":
    unittest.main()
