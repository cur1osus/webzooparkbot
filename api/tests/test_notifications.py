"""Regression coverage for transactional notifications and stale-income boundaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from api.app.core.notification_worker import NotificationWorker
from api.app.db.connection import get_session
from api.app.db.models import Animal, NotificationOutbox, Player
from api.app.routes import telegram_webhook as webhook
from api.app.zoopark import income as income_module
from api.app.zoopark.notifications import enqueue_unclaimed_daily_bonuses
from api.app.zoopark.season import active_season
from api.app.zoopark.status import daily_bonus


def test_natural_death_settles_old_rate_and_enqueues_once(db, player, monkeypatch):
    start = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
    death = start + timedelta(minutes=10)
    now = start + timedelta(minutes=20)
    monkeypatch.setattr(income_module, "utcnow", lambda: now)

    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        season = active_season(session)
        row.income_synced_at = start
        row.income_rub_per_min = 100
        row.upkeep_rub_per_min = 0
        session.add(
            Animal(
                player_id=row.id,
                season_id=season.id,
                species_id=1,
                name="Кролик",
                habitat="forest",
                origin="pack",
                gene_survival="low",
                gene_reproduction="low",
                gene_appearance="low",
                gene_size="low",
                acquired_at=start,
                dies_at=death,
            )
        )
        session.commit()

    with get_session() as session:
        row = session.query(Player).filter_by(telegram_id=player).one()
        income_module.sync_player_income(session, row)
        outbox = session.query(NotificationOutbox).all()
        # Registration grants the starter 1,000 ₽; the dead animal contributes exactly
        # the ten minutes before its death, not the ten minutes after it.
        assert row.balance_rub == 2000
        assert len(outbox) == 1
        assert "Кролик" in outbox[0].payload_json
        session.commit()


def test_daily_bonus_is_durable_and_worker_retries_then_sends(db, player, monkeypatch):
    daily_bonus(player)
    with get_session() as session:
        assert enqueue_unclaimed_daily_bonuses(session) == 1
        session.commit()

    worker = NotificationWorker()
    with patch("api.app.core.notification_worker.call_bot_api", side_effect=[RuntimeError("offline"), {"ok": True}]) as send:
        assert worker.dispatch_due() == 1
        with get_session() as session:
            row = session.query(NotificationOutbox).one()
            row.available_at = row.created_at
            session.commit()
        assert worker.dispatch_due() == 1
        assert send.call_count == 2

    with get_session() as session:
        row = session.query(NotificationOutbox).one()
        assert row.sent_at is not None
        assert row.attempts == 2


def test_webhook_does_not_mark_failed_side_effect_as_processed(db, monkeypatch):
    monkeypatch.setattr(webhook, "TELEGRAM_WEBHOOK_SECRET", "secret")

    def fail_once(_query):
        raise RuntimeError("temporary")

    monkeypatch.setattr(webhook, "_handle_pre_checkout", fail_once)

    with pytest.raises(RuntimeError, match="temporary"):
        webhook.telegram_webhook({"update_id": 7001, "pre_checkout_query": {"id": "q"}}, "secret")
    assert webhook._update_was_processed(7001) is False

    monkeypatch.setattr(webhook, "_handle_pre_checkout", lambda _query: None)
    webhook.telegram_webhook({"update_id": 7001, "pre_checkout_query": {"id": "q"}}, "secret")
    assert webhook._update_was_processed(7001) is True
