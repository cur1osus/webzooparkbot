from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from api.app.core.config import BOT_TOKEN

logger = logging.getLogger(__name__)

BOT_API_TIMEOUT_SECONDS = 10


class TelegramApiError(RuntimeError):
    pass


def call_bot_api(method: str, payload: dict) -> dict:
    if not BOT_TOKEN:
        raise TelegramApiError("Бот не настроен")

    request = urllib.request.Request(  # noqa: S310 — fixed https host, no user-controlled scheme
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=BOT_API_TIMEOUT_SECONDS) as response:  # noqa: S310
            data = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.exception("Bot API call %s failed", method)
        raise TelegramApiError(f"Ошибка Bot API: {exc}") from exc

    if not data.get("ok"):
        description = data.get("description", "Bot API error")
        logger.error("Bot API %s rejected the call: %s", method, description)
        raise TelegramApiError(description)
    return data
