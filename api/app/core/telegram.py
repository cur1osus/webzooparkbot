from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from api.app.core.config import BOT_TOKEN

logger = logging.getLogger(__name__)

BOT_API_TIMEOUT_SECONDS = 10


class TelegramApiError(RuntimeError):
    """A failed Bot API call, carrying enough to decide whether retrying is worth it."""

    def __init__(self, message: str, *, status: int | None = None, description: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.description = description

    @property
    def permanent(self) -> bool:
        """True when no number of retries will ever deliver this message.

        Telegram answers 400 for "chat not found" — a player who opened the mini app from a
        link but never pressed Start in the bot — and 403 for "bot was blocked" or a
        deleted account. Both are settled facts about the recipient. A malformed payload is
        also a 400 and equally hopeless for that row.

        Everything else (429, 5xx, a dropped connection) is the network or a rate limit,
        and those do clear.
        """
        return self.status in {400, 403}


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
    except urllib.error.HTTPError as exc:
        # Telegram puts the real reason in a JSON body even on a 4xx, and that reason is
        # what separates "this chat will never exist" from "slow down". Logged at warning,
        # not exception: an unreachable player is ordinary, and a stack trace per retry is
        # what buried the real errors in the journal.
        description = ""
        try:
            description = str(json.loads(exc.read()).get("description", ""))
        except (ValueError, OSError):
            pass
        logger.warning("Bot API %s failed: HTTP %s %s", method, exc.code, description)
        raise TelegramApiError(
            f"Ошибка Bot API: HTTP {exc.code} {description}".strip(),
            status=exc.code,
            description=description,
        ) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("Bot API call %s failed: %s", method, exc)
        raise TelegramApiError(f"Ошибка Bot API: {exc}") from exc

    if not data.get("ok"):
        description = data.get("description", "Bot API error")
        logger.error("Bot API %s rejected the call: %s", method, description)
        raise TelegramApiError(description, status=int(data.get("error_code") or 0) or None, description=description)
    return data
