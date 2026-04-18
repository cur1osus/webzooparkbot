from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import parse_qsl

from fastapi import Request

from api.app.config import settings
from api.app.core.errors import AppError


def parse_init_data(init_data: str) -> dict[str, str]:
    return dict(parse_qsl(init_data, keep_blank_values=True))


def validate_init_data(init_data: str, dev_user_id: str = "") -> int:
    if settings.dev_mode and dev_user_id:
        try:
            return int(dev_user_id)
        except ValueError as exc:
            raise AppError("Invalid X-Dev-User-Id header", status_code=401) from exc

    if not init_data:
        raise AppError("Missing X-Init-Data header", status_code=401)

    params = parse_init_data(init_data)
    received_hash = params.pop("hash", "")
    data_check = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(received_hash, expected_hash):
        raise AppError("Invalid initData signature", status_code=401)

    user = json.loads(params.get("user", "{}"))
    telegram_id = user.get("id")
    if not telegram_id:
        raise AppError("No user in initData", status_code=401)
    return int(telegram_id)


def require_telegram_id(request: Request) -> int:
    return validate_init_data(
        init_data=request.headers.get("X-Init-Data", ""),
        dev_user_id=request.headers.get("X-Dev-User-Id", ""),
    )
