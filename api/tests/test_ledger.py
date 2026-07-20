"""The ledger is the only door currency moves through."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from api.app.db.connection import get_session
from api.app.db.models import LedgerEntry, Player, TreasuryLedgerEntry
from api.app.zoopark import ledger
from api.app.zoopark.progression import open_pack

DOMAIN = Path(__file__).resolve().parents[1] / "app" / "zoopark"
DIRECT_ASSIGNMENT = re.compile(r"\.balance_(rub|usd|paw)\s*(\+=|-=|=)[^=]")


def test_no_module_assigns_a_balance_directly():
    """`grant()` writes the ledger row; a bare `player.balance_rub += x` would not."""
    offenders = []
    for path in DOMAIN.glob("*.py"):
        if path.name == "ledger.py":
            continue
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if DIRECT_ASSIGNMENT.search(line):
                offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert not offenders, "balances must move through ledger.grant():\n" + "\n".join(offenders)


def test_grant_records_the_balance_it_produced(db, player):
    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        ledger.grant(session, row, "rub", 500, "daily_bonus")
        ledger.spend(session, row, "rub", 200, "pack_open")
        session.commit()

        entries = session.query(LedgerEntry).order_by(LedgerEntry.id).all()
        assert [(e.delta, e.balance_after) for e in entries[-2:]] == [(500, 500), (-200, 300)]


def test_overdrawing_moves_nothing(db, player):
    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        with pytest.raises(ledger.InsufficientFunds):
            ledger.spend(session, row, "rub", 1, "pack_open")
        assert row.balance_rub == 0
        assert session.query(LedgerEntry).filter_by(currency="rub").count() == 0


def test_a_zero_delta_writes_no_row(db, player):
    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        before = session.query(LedgerEntry).count()
        ledger.grant(session, row, "rub", 0, "daily_bonus")
        assert session.query(LedgerEntry).count() == before


def test_ledger_reconciles_with_every_balance(db, player, grant):
    grant(player, "usd", 10 ** 9)  # paid packs cost dollars
    open_pack(player)          # free daily gift
    open_pack(player, "rare")  # a paid pack

    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        for currency in ("rub", "usd", "paw"):
            total, stored = ledger.reconcile(session, row.id, currency)
            assert total == stored, f"{currency}: ledger says {total}, balance says {stored}"


def test_treasury_is_keyed_by_currency(db):
    with get_session() as session:
        ledger.credit_treasury(session, "usd", 10, "bank_fee")
        ledger.credit_treasury(session, "usd", 5, "bank_fee")
        session.commit()
        assert ledger.treasury_balance(session, "usd") == 15
        assert ledger.treasury_balance(session, "rub") == 0


def test_the_treasury_journal_reconciles_with_the_row(db):
    """The same guarantee the player ledger gives, for the house. Without it the safe could
    move tens of thousands of dollars a week and leave nothing to audit."""
    with get_session() as session:
        ledger.credit_treasury(session, "usd", 1000, "bank_fee")
        ledger.debit_treasury(session, "usd", 400, "safe_prize", ref_table="safe_rounds", ref_id=7)
        ledger.credit_treasury(session, "usd", 25, "bank_fee")
        session.commit()

    with get_session() as session:
        total, stored = ledger.reconcile_treasury(session, "usd")
        assert total == stored == 625
        rows = session.query(TreasuryLedgerEntry).order_by(TreasuryLedgerEntry.id).all()
        assert [row.delta for row in rows] == [1000, -400, 25]
        # `balance_after` makes the journal readable on its own, without re-summing it.
        assert [row.balance_after for row in rows] == [1000, 600, 625]
        assert [row.reason for row in rows] == ["bank_fee", "safe_prize", "bank_fee"]
        assert (rows[1].ref_table, rows[1].ref_id) == ("safe_rounds", 7)


def test_a_capped_debit_journals_what_it_actually_took(db):
    """`debit_treasury` is capped at the balance. Booking the requested amount instead of
    the taken one would make the journal disagree with the row on the very first overdraw."""
    with get_session() as session:
        ledger.credit_treasury(session, "usd", 100, "bank_fee")
        taken = ledger.debit_treasury(session, "usd", 250, "safe_prize")
        session.commit()
        assert taken == 100

    with get_session() as session:
        total, stored = ledger.reconcile_treasury(session, "usd")
        assert total == stored == 0


def test_a_refused_movement_writes_nothing(db):
    with get_session() as session:
        ledger.credit_treasury(session, "usd", 0, "bank_fee")
        ledger.debit_treasury(session, "usd", 50, "safe_prize")  # empty treasury
        session.commit()
        assert session.query(TreasuryLedgerEntry).count() == 0
