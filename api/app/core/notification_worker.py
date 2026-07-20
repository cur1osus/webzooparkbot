"""Background delivery for the durable Telegram notification outbox."""

from __future__ import annotations

import json
import logging
import threading
from datetime import timedelta

from sqlalchemy import or_, select

from api.app.core.telegram import TelegramApiError, call_bot_api
from api.app.db.connection import get_session
from api.app.db.models import NotificationOutbox, Player, utcnow
from api.app.zoopark.notifications import (
    enqueue_natural_death_notifications,
    enqueue_safe_cracked,
    enqueue_safe_opened,
    enqueue_unclaimed_daily_bonuses,
)
from api.app.zoopark.safe import resolve_due_days

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
                        # The safe pays real money, so it resolves on this scan rather
                        # than lazily on a request: a day must close and pay out whether
                        # or not anyone opens the app afterwards.
                        cracked = resolve_due_days(session)
                        if cracked is not None:
                            enqueue_safe_cracked(session, cracked)
                        enqueue_safe_opened(session)
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
                # Outer join: a broadcast row addresses a chat and has no player at all.
                select(NotificationOutbox, Player.telegram_id)
                .outerjoin(Player, Player.id == NotificationOutbox.player_id)
                .where(
                    NotificationOutbox.sent_at.is_(None),
                    NotificationOutbox.failed_at.is_(None),
                    NotificationOutbox.available_at <= now,
                    or_(
                        NotificationOutbox.locked_at.is_(None),
                        NotificationOutbox.locked_at < stale_before,
                    ),
                )
                .order_by(NotificationOutbox.id.asc())
                .limit(limit)
                .with_for_update(skip_locked=True, of=NotificationOutbox)
            ).all()
            claimed: list[tuple[int, int, str, int]] = []
            for outbox, telegram_id in rows:
                recipient = telegram_id if outbox.player_id is not None else outbox.chat_id
                if recipient is None:
                    # A player row whose player vanished. Nothing to deliver to, ever.
                    outbox.failed_at = now
                    outbox.last_error = "нет адресата"
                    continue
                outbox.locked_at = now
                outbox.attempts += 1
                claimed.append((outbox.id, recipient, outbox.payload_json, outbox.attempts))
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
        permanent = isinstance(error, TelegramApiError) and error.permanent
        delay = min(3600, 5 * (2 ** min(max(attempts - 1, 0), 8)))
        with get_session() as session:
            row = session.get(NotificationOutbox, outbox_id, with_for_update=True)
            if row is not None and row.sent_at is None:
                if permanent:
                    # The recipient is unreachable, not busy. Retrying this hourly forever
                    # is what filled the queue with dead rows and the journal with noise.
                    row.failed_at = utcnow()
                else:
                    row.available_at = utcnow() + timedelta(seconds=delay)
                row.locked_at = None
                row.last_error = str(error)[:512]
            session.commit()
