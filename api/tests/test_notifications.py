"""Regression coverage for transactional notifications and stale-income boundaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from api.app.core.config import SOCIAL_REWARD_CHAT_ID
from api.app.core.notification_worker import NotificationWorker
from api.app.core.telegram import TelegramApiError
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


def test_a_permanently_undeliverable_message_is_given_up_on(db, player, monkeypatch):
    """A player who never pressed Start in the bot answers 400 forever. Retrying that
    hourly is what left 42 dead rows in the queue and buried real errors in the journal."""
    daily_bonus(player)
    with get_session() as session:
        enqueue_unclaimed_daily_bonuses(session)
        session.commit()

    blocked = TelegramApiError("chat not found", status=400, description="Bad Request: chat not found")
    worker = NotificationWorker()
    with patch("api.app.core.notification_worker.call_bot_api", side_effect=blocked):
        assert worker.dispatch_due() == 1

    with get_session() as session:
        row = session.query(NotificationOutbox).one()
        assert row.failed_at is not None, "a permanent refusal must end the row"
        assert row.sent_at is None

    # And it is never claimed again, however long the worker runs.
    with patch("api.app.core.notification_worker.call_bot_api") as send:
        assert worker.dispatch_due() == 0
        assert send.call_count == 0


def test_a_rate_limit_is_still_retried(db, player, monkeypatch):
    daily_bonus(player)
    with get_session() as session:
        enqueue_unclaimed_daily_bonuses(session)
        session.commit()

    throttled = TelegramApiError("Too Many Requests", status=429, description="Too Many Requests")
    worker = NotificationWorker()
    with patch("api.app.core.notification_worker.call_bot_api", side_effect=throttled):
        assert worker.dispatch_due() == 1

    with get_session() as session:
        row = session.query(NotificationOutbox).one()
        assert row.failed_at is None, "429 clears on its own; it must not end the row"
        assert row.available_at > row.created_at


@pytest.mark.parametrize(
    ("status", "permanent"),
    [(400, True), (403, True), (429, False), (500, False), (None, False)],
)
def test_which_bot_api_failures_are_worth_retrying(status, permanent):
    assert TelegramApiError("x", status=status).permanent is permanent


def test_the_safe_announcement_goes_to_the_chat_not_to_inboxes(db, player, monkeypatch):
    """Twenty identical DMs is how a bot gets muted; the safe is one shared race, so it is
    announced once in the community chat."""
    from datetime import date as _date

    from api.app.zoopark import notifications as notifications_module
    from api.app.zoopark import safe

    midwindow = datetime(2026, 7, 20, 17, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(safe, "utcnow", lambda: midwindow)
    monkeypatch.setattr(notifications_module, "utcnow", lambda: midwindow)

    with get_session() as session:
        assert notifications_module.enqueue_safe_opened(session) is True
        session.commit()

    with get_session() as session:
        rows = session.query(NotificationOutbox).filter_by(kind="safe_opened").all()
        assert len(rows) == 1, "one message for everybody, not one per player"
        assert rows[0].player_id is None
        assert rows[0].chat_id == SOCIAL_REWARD_CHAT_ID

    # A second scan the same day must not post again.
    with get_session() as session:
        assert notifications_module.enqueue_safe_opened(session) is False
        session.commit()
    with get_session() as session:
        assert session.query(NotificationOutbox).filter_by(kind="safe_opened").count() == 1
        assert _date(2026, 7, 20).isoformat() in session.query(NotificationOutbox).filter_by(
            kind="safe_opened"
        ).one().dedupe_key


def test_a_chat_broadcast_is_delivered_to_the_chat_id(db, monkeypatch):
    from api.app.zoopark.notifications import enqueue_chat

    with get_session() as session:
        assert enqueue_chat(session, chat_id=-100123, kind="safe_opened", dedupe_key="k", text="привет") is True
        session.commit()

    worker = NotificationWorker()
    with patch("api.app.core.notification_worker.call_bot_api", return_value={"ok": True}) as send:
        assert worker.dispatch_due() == 1
        assert send.call_args[0][1]["chat_id"] == -100123


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
