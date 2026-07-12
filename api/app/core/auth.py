from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException

from api.app.core.config import (
    ALLOWED_TG_IDS,
    BOT_TOKEN,
    CLOSED_MSG,
    DEV_AUTH,
    INIT_DATA_MAX_AGE_SECONDS,
)

logger = logging.getLogger(__name__)


def _verified_init_data(x_init_data: str) -> dict[str, str]:
    # parse_qsl already percent-decodes once, which is exactly how Telegram signed the values.
    # Decoding a second time (e.g. via unquote first) corrupts names containing '+' or '&'.
    params = dict(parse_qsl(x_init_data, keep_blank_values=True))
    received_hash = params.pop("hash", "")
    if not received_hash:
        raise HTTPException(401, "Unauthorized")

    data_check = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        logger.warning("initData signature mismatch")
        raise HTTPException(401, "Unauthorized")

    try:
        auth_date = int(params.get("auth_date", "0"))
    except ValueError:
        auth_date = 0
    if auth_date <= 0 or time.time() - auth_date > INIT_DATA_MAX_AGE_SECONDS:
        logger.warning("initData expired (auth_date=%s)", auth_date)
        raise HTTPException(401, "Session expired, reopen the app")

    return params


def parse_tg_id(x_init_data: str, x_dev_user_id: str) -> int:
    if x_dev_user_id:
        if not DEV_AUTH:
            logger.warning("X-Dev-User-Id supplied while DEV_AUTH is disabled")
            raise HTTPException(401, "Unauthorized")
        try:
            return int(x_dev_user_id)
        except ValueError as exc:
            raise HTTPException(401, "Bad dev user id") from exc

    if not x_init_data:
        raise HTTPException(401, "Unauthorized")

    if not BOT_TOKEN:
        # Never fall back to trusting an unsigned payload.
        logger.error("BOT_TOKEN is not configured, refusing to verify initData")
        raise HTTPException(503, "Authentication is not configured")

    params = _verified_init_data(x_init_data)

    try:
        user = json.loads(params.get("user", "{}"))
        tg_id = int(user["id"])
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning("initData carries no usable user id: %s", exc)
        raise HTTPException(401, "Unauthorized") from exc

    return tg_id


def auth(x_init_data: str, x_dev_user_id: str) -> int:
    tg_id = parse_tg_id(x_init_data, x_dev_user_id)
    if ALLOWED_TG_IDS is not None and tg_id not in ALLOWED_TG_IDS:
        raise HTTPException(403, CLOSED_MSG)
    return tg_id
