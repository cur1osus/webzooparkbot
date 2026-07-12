"""Telegram Stars: credited exactly once, and taken back when Telegram refunds them."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.app.db.connection import get_session
from api.app.db.models import Player, StarPayment
from api.app.routes import telegram_webhook as webhook
from api.app.zoopark import ledger
from api.app.zoopark.catalog import STARS_TO_PAW
from api.app.zoopark.games import credit_star_payment, refund_star_payment


def _paw(telegram_id: int) -> int:
    with get_session() as session:
        return ledger.balance(session.query(Player).filter_by(telegram_id=telegram_id).one(), "paw")


class TestCrediting:
    def test_a_payment_credits_once(self, db, player):
        assert credit_star_payment(player, "charge_1", 100) is True
        assert _paw(player) == 100 * STARS_TO_PAW

    def test_a_replayed_webhook_does_not_credit_twice(self, db, player):
        credit_star_payment(player, "charge_1", 100)
        assert credit_star_payment(player, "charge_1", 100) is False
        assert _paw(player) == 100 * STARS_TO_PAW

    def test_an_unknown_player_is_not_credited(self, db):
        assert credit_star_payment(999_999, "charge_1", 100) is False

    def test_a_malformed_payment_is_dropped(self, db, player):
        assert credit_star_payment(player, "", 100) is False
        assert credit_star_payment(player, "charge_1", 0) is False
        assert _paw(player) == 0


class TestRefunds:
    """I-4: nothing handled `refunded_payment`, so a player could buy PawCoins, ask
    Telegram for the Stars back, and keep both."""

    def test_a_refund_claws_the_paw_coins_back(self, db, player):
        credit_star_payment(player, "charge_1", 100)
        assert refund_star_payment("charge_1") is True
        assert _paw(player) == 0

        with get_session() as session:
            assert session.get(StarPayment, "charge_1").refunded_at is not None

    def test_a_refund_of_already_spent_coins_stops_at_zero(self, db, player):
        credit_star_payment(player, "charge_1", 100)
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=player).one()
            ledger.spend(session, row, "paw", 900, "forge_create")
            session.commit()

        assert refund_star_payment("charge_1") is True
        assert _paw(player) == 0

    def test_refunding_twice_is_a_no_op(self, db, player):
        credit_star_payment(player, "charge_1", 100)
        assert refund_star_payment("charge_1") is True
        assert refund_star_payment("charge_1") is False

    def test_refunding_an_unknown_charge_is_a_no_op(self, db):
        assert refund_star_payment("nope") is False


class TestWebhook:
    def test_it_is_a_sync_handler(self):
        """C-3: as `async def` it ran on the event loop, where a 10-second Bot API call and
        a `SELECT … FOR UPDATE` could freeze every request for every player."""
        import inspect

        assert not inspect.iscoroutinefunction(webhook.telegram_webhook)

    def test_a_missing_secret_refuses(self, monkeypatch):
        monkeypatch.setattr(webhook, "TELEGRAM_WEBHOOK_SECRET", "")
        with pytest.raises(HTTPException) as exc:
            webhook._authorize("anything")
        assert exc.value.status_code == 503

    def test_a_wrong_secret_is_forbidden(self, monkeypatch):
        monkeypatch.setattr(webhook, "TELEGRAM_WEBHOOK_SECRET", "right")
        with pytest.raises(HTTPException) as exc:
            webhook._authorize("wrong")
        assert exc.value.status_code == 403

    def test_a_matching_secret_passes(self, monkeypatch):
        monkeypatch.setattr(webhook, "TELEGRAM_WEBHOOK_SECRET", "right")
        webhook._authorize("right")

    def test_an_update_is_processed_once(self, db):
        assert webhook._claim_update(42) is True
        assert webhook._claim_update(42) is False

    def test_a_non_star_currency_is_refused(self, db, player):
        """`total_amount` means Stars only for XTR; for a fiat invoice it is minor units."""
        webhook._handle_successful_payment(
            {
                "from": {"id": player},
                "successful_payment": {
                    "currency": "RUB",
                    "total_amount": 10_000,
                    "telegram_payment_charge_id": "charge_fiat",
                },
            }
        )
        assert _paw(player) == 0

    def test_the_credited_amount_comes_from_telegram_not_the_payload(self, db, player):
        webhook._handle_successful_payment(
            {
                "from": {"id": player},
                "successful_payment": {
                    "currency": "XTR",
                    "total_amount": 50,
                    "invoice_payload": "donate_1001_999999",
                    "telegram_payment_charge_id": "charge_2",
                },
            }
        )
        assert _paw(player) == 50 * STARS_TO_PAW

    def test_a_refunded_payment_is_handled(self, db, player):
        credit_star_payment(player, "charge_3", 10)
        webhook._handle_refunded_payment({"refunded_payment": {"telegram_payment_charge_id": "charge_3"}})
        assert _paw(player) == 0

    def test_pre_checkout_is_answered(self, db):
        with patch.object(webhook, "call_bot_api") as call:
            webhook._handle_pre_checkout({"id": "q1"})
        call.assert_called_once_with("answerPreCheckoutQuery", {"pre_checkout_query_id": "q1", "ok": True})
