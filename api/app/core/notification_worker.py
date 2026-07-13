"""Background delivery for the durable Telegram notification outbox."""

from __future__ import annotations

import json
import logging
import threading
from datetime import timedelta

from sqlalchemy import or_, select

from api.app.core.telegram import call_bot_api
from api.app.db.connection import get_session
from api.app.db.models import NotificationOutbox, Player, utcnow
from api.app.zoopark.notifications import enqueue_natural_death_notifications, enqueue_unclaimed_daily_bonuses

logger = logging.getLogger(__name__)


class NotificationWorker:
    def __init__(self, *, poll_seconds: float = 5.0) -> None:
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="telegram-notifications", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=15)
            self._thread = None

    def _run(self) -> None:
        next_bonus_scan = 0.0
        elapsed = 0.0
        while not self._stop.is_set():
            try:
                if elapsed >= next_bonus_scan:
                    with get_session() as session:
                        enqueue_unclaimed_daily_bonuses(session)
                        enqueue_natural_death_notifications(session)
                        session.commit()
                    next_bonus_scan = elapsed + 60.0
                self.dispatch_due()
            except Exception:
                logger.exception("Telegram notification worker iteration failed")
            self._stop.wait(self.poll_seconds)
            elapsed += self.poll_seconds

    def dispatch_due(self, *, limit: int = 20) -> int:
        now = utcnow()
        stale_before = now - timedelta(minutes=5)
        with get_session() as session:
            rows = session.execute(
                select(NotificationOutbox, Player.telegram_id)
                .join(Player, Player.id == NotificationOutbox.player_id)
                .where(
                    NotificationOutbox.sent_at.is_(None),
                    NotificationOutbox.available_at <= now,
                    or_(
                        NotificationOutbox.locked_at.is_(None),
                        NotificationOutbox.locked_at < stale_before,
                    ),
                )
                .order_by(NotificationOutbox.id.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            ).all()
            claimed: list[tuple[int, int, str, int]] = []
            for outbox, telegram_id in rows:
                outbox.locked_at = now
                outbox.attempts += 1
                claimed.append((outbox.id, telegram_id, outbox.payload_json, outbox.attempts))
            session.commit()

        for outbox_id, telegram_id, payload_json, attempts in claimed:
            try:
                payload = json.loads(payload_json)
                call_bot_api(
                    "sendMessage",
                    {
                        "chat_id": telegram_id,
                        "text": payload["text"],
                        "disable_web_page_preview": True,
                    },
                )
            except Exception as exc:
                self._mark_failed(outbox_id, attempts, exc)
            else:
                self._mark_sent(outbox_id)
        return len(claimed)

    @staticmethod
    def _mark_sent(outbox_id: int) -> None:
        with get_session() as session:
            row = session.get(NotificationOutbox, outbox_id, with_for_update=True)
            if row is not None and row.sent_at is None:
                row.sent_at = utcnow()
                row.locked_at = None
                row.last_error = None
            session.commit()

    @staticmethod
    def _mark_failed(outbox_id: int, attempts: int, error: Exception) -> None:
        delay = min(3600, 5 * (2 ** min(max(attempts - 1, 0), 8)))
        with get_session() as session:
            row = session.get(NotificationOutbox, outbox_id, with_for_update=True)
            if row is not None and row.sent_at is None:
                row.available_at = utcnow() + timedelta(seconds=delay)
                row.locked_at = None
                row.last_error = str(error)[:512]
            session.commit()
