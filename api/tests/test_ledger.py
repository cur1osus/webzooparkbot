"""The ledger is the only door currency moves through."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from api.app.db.connection import get_session
from api.app.db.models import LedgerEntry, Player
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
        ledger.credit_treasury(session, "usd", 10)
        ledger.credit_treasury(session, "usd", 5)
        session.commit()
        assert ledger.treasury_balance(session, "usd") == 15
        assert ledger.treasury_balance(session, "rub") == 0
