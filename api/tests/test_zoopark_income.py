from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from api.app.zoopark import income as income_module


UTC = timezone.utc


class _FixedDateTime:
    current = datetime(2026, 4, 18, 12, 0, tzinfo=UTC)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.current.replace(tzinfo=None)
        return cls.current.astimezone(tz)


class ZooParkIncomeTests(unittest.TestCase):
    def test_accrue_income_uses_net_income(self) -> None:
        session = MagicMock()
        user = SimpleNamespace(id=1, rub=100, last_income_at=_FixedDateTime.current - timedelta(minutes=2), balance_seq=0)

        with patch.object(income_module, "datetime", _FixedDateTime):
            result = income_module.accrue_income(session, user, income_rub_per_min=120, expenses_rub_per_min=30)

        self.assertEqual(result.rub, 280)
        self.assertEqual(user.balance_seq, int(_FixedDateTime.current.timestamp() * 1000))

    def test_accrue_income_never_drops_below_zero(self) -> None:
        session = MagicMock()
        user = SimpleNamespace(id=2, rub=50, last_income_at=_FixedDateTime.current - timedelta(minutes=1), balance_seq=0)

        with patch.object(income_module, "datetime", _FixedDateTime):
            result = income_module.accrue_income(session, user, income_rub_per_min=0, expenses_rub_per_min=120)

        self.assertEqual(result.rub, 0)

    def test_sync_passive_balance_uses_pack_income(self) -> None:
        session = MagicMock()
        user = SimpleNamespace(id=3, rub=100)

        with patch.object(income_module, "datetime", _FixedDateTime), \
             patch.object(income_module, "calc_pack_income", return_value=50), \
             patch.object(income_module, "calc_sick_expenses", return_value=10), \
             patch.object(income_module, "accrue_income", return_value=SimpleNamespace(id=3, rub=380)):
            updated_user, income_rub_per_min, expenses_rub_per_min = income_module.sync_passive_balance(session, user)

        self.assertEqual(income_rub_per_min, 50)
        self.assertEqual(expenses_rub_per_min, 10)
        self.assertEqual(updated_user.rub, 380)


if __name__ == "__main__":
    unittest.main()
