"""Telegram webhook.

Declared `def`, not `async def`, on purpose. FastAPI runs a sync handler in the thread
pool; an async one runs on the event loop, and everything this handler does is blocking —
a `urllib` call to api.telegram.org (up to 10s) and a `SELECT … FOR UPDATE` that can wait
on a lock the paying player's own request is holding. As an `async def` on a single-worker
uvicorn, one webhook could freeze every request for every player until MySQL's lock timeout.
"""

from __future__ import annotations

import hmac
import logging
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException
from sqlalchemy.exc import IntegrityError

from api.app.core.config import TELEGRAM_WEBHOOK_SECRET
from api.app.core.telegram import TelegramApiError, call_bot_api
from api.app.db.connection import get_session
from api.app.db.models import TelegramUpdate
from api.app.zoopark.games import credit_star_payment, refund_star_payment

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telegram"])


def _authorize(secret_token: str) -> None:
    if not TELEGRAM_WEBHOOK_SECRET:
        logger.error("TELEGRAM_WEBHOOK_SECRET is not configured, refusing webhook")
        raise HTTPException(503, "Webhook is not configured")
    if not hmac.compare_digest(secret_token, TELEGRAM_WEBHOOK_SECRET):
        logger.warning("Webhook called with a bad secret token")
        raise HTTPException(403, "Forbidden")


def _claim_update(update_id: int) -> bool:
    """False if Telegram has already delivered this update. Idempotency for every kind
    of update, not only the two that move money."""
    with get_session() as session:
        session.add(TelegramUpdate(update_id=update_id))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return False
    return True


def _handle_pre_checkout(query: dict[str, Any]) -> None:
    try:
        call_bot_api("answerPreCheckoutQuery", {"pre_checkout_query_id": query["id"], "ok": True})
    except (TelegramApiError, KeyError):
        logger.exception("Failed to answer pre_checkout_query")


def _handle_successful_payment(message: dict[str, Any]) -> None:
    payment = message.get("successful_payment") or {}
    payer = message.get("from") or {}

    if payment.get("currency") != "XTR":
        # `total_amount` means Stars only for XTR. For a fiat invoice it is minor units,
        # and crediting it as Stars would multiply the payout by a hundred.
        logger.error("successful_payment in unexpected currency %r", payment.get("currency"))
        return

    charge_id = payment.get("telegram_payment_charge_id", "")
    stars = int(payment.get("total_amount") or 0)
    telegram_id = payer.get("id")

    if not charge_id or not telegram_id:
        logger.error("successful_payment without charge id or payer: %s", payment)
        return

    credit_star_payment(int(telegram_id), charge_id, stars)


def _handle_refunded_payment(message: dict[str, Any]) -> None:
    payment = message.get("refunded_payment") or {}
    charge_id = payment.get("telegram_payment_charge_id", "")
    if not charge_id:
        logger.error("refunded_payment without charge id: %s", payment)
        return
    refund_star_payment(charge_id)


@router.post("/api/telegram/webhook")
def telegram_webhook(
    update: dict[str, Any] = Body(...),
    x_telegram_bot_api_secret_token: str = Header(default=""),
) -> dict:
    _authorize(x_telegram_bot_api_secret_token)

    update_id = update.get("update_id")
    if isinstance(update_id, int) and not _claim_update(update_id):
        logger.info("Update %s already processed", update_id)
        return {"ok": True}

    if isinstance(update.get("pre_checkout_query"), dict):
        _handle_pre_checkout(update["pre_checkout_query"])
    elif isinstance(update.get("message"), dict):
        message = update["message"]
        if "successful_payment" in message:
            _handle_successful_payment(message)
        elif "refunded_payment" in message:
            _handle_refunded_payment(message)

    # Always 200: a non-2xx makes Telegram retry the same update indefinitely.
    return {"ok": True}
