from __future__ import annotations

from api.app.db.connection import get_session
from api.app.db.models import LedgerEntry, Player
from api.app.zoopark import ledger, subscriptions


def test_subscription_reward_is_idempotent_and_clawback_can_go_negative(db, player):
    target = subscriptions.TARGETS[0]

    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        assert subscriptions.apply_membership(session, row, target, True) == 50
        assert subscriptions.apply_membership(session, row, target, True) == 0
        assert ledger.balance(row, "paw") == 50
        ledger.spend(session, row, "paw", 50, "forge_create")
        assert subscriptions.apply_membership(session, row, target, False) == -50
        assert subscriptions.apply_membership(session, row, target, False) == 0
        session.commit()

    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        assert ledger.balance(row, "paw") == -50
        entries = session.query(LedgerEntry).filter_by(player_id=row.id, currency="paw").all()
        assert [entry.delta for entry in entries] == [50, -50, -50]


def test_restricted_member_status_counts_only_when_telegram_marks_membership_true():
    assert subscriptions.is_member_status({"status": "restricted", "is_member": True}) is True
    assert subscriptions.is_member_status({"status": "restricted", "is_member": False}) is False
    assert subscriptions.is_member_status({"status": "left"}) is False
