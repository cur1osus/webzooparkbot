from __future__ import annotations

import os

from api.app.zoopark.catalog import SOCIAL_SUBSCRIPTION_REWARD_PAW


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _env_allowed_ids(name: str, default: str) -> set[int] | None:
    """`*` (or an empty value) opens the game to everyone; otherwise a CSV whitelist."""
    raw = os.getenv(name, default).strip()
    if raw in {"*", ""}:
        return None
    return {int(part) for part in raw.split(",") if part.strip()}


def _env_origins(name: str, default: str) -> list[str]:
    return [origin.strip() for origin in os.getenv(name, default).split(",") if origin.strip()]


APP_ENV = os.getenv("APP_ENV", "production")
if APP_ENV not in {"development", "staging", "production"}:
    raise RuntimeError("APP_ENV must be one of: development, staging, production")
IS_PRODUCTION = APP_ENV == "production"

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "ZooParkBot")

# PawCoins reward for staying subscribed to the official ZooPark channel and chat. The
# IDs are public Telegram chat IDs; keeping them configurable lets the campaign move later
# without a code change while the defaults match the current production communities.
SOCIAL_REWARD_AMOUNT = _env_int("SOCIAL_REWARD_AMOUNT", SOCIAL_SUBSCRIPTION_REWARD_PAW)
SOCIAL_REWARD_CHANNEL_ID = _env_int("SOCIAL_REWARD_CHANNEL_ID", -1002099627259)
SOCIAL_REWARD_CHANNEL_URL = os.getenv("SOCIAL_REWARD_CHANNEL_URL", "https://t.me/newsZooPark")
SOCIAL_REWARD_CHAT_ID = _env_int("SOCIAL_REWARD_CHAT_ID", -1002073914350)
SOCIAL_REWARD_CHAT_URL = os.getenv("SOCIAL_REWARD_CHAT_URL", "https://t.me/ZooPark_4at")

# When true, the X-Dev-User-Id header may impersonate a player without a Telegram signature.
DEV_AUTH = _env_flag("DEV_AUTH", default=False)

# initData older than this is rejected, so a captured payload cannot be replayed forever.
INIT_DATA_MAX_AGE_SECONDS = int(os.getenv("INIT_DATA_MAX_AGE_SECONDS", "86400"))

ALLOWED_TG_IDS: set[int] | None = _env_allowed_ids("ALLOWED_TG_IDS", "474701274")
# Admin access is deliberately a separate allowlist. Keeping it outside the frontend
# makes the panel safe even if someone reveals the Mini App bundle.
ADMIN_TG_IDS: set[int] = _env_allowed_ids("ADMIN_TG_IDS", "474701274") or set()
CLOSED_MSG = "🚧 Игра в разработке. Скоро открытие — следи за обновлениями!"
CORS_ORIGINS = _env_origins("CORS_ORIGINS", "http://localhost:5173" if not IS_PRODUCTION else "")

# Shared secret Telegram echoes back in X-Telegram-Bot-Api-Secret-Token on every webhook call.
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

# AI rivals. Read by the bot runner only; the API process never calls the model, so a
# missing key degrades the rivals to their fallback plans and leaves the game untouched.
ROUTERAI_API_KEY = os.getenv("ROUTERAI_API_KEY", "")
ROUTERAI_BASE_URL = os.getenv("ROUTERAI_BASE_URL", "https://routerai.ru/api/v1")
BOT_PLANNER_MODEL = os.getenv("BOT_PLANNER_MODEL", "deepseek/deepseek-v4-flash")

# `BANK_RATE_SECRET` is gone. It existed because the rate was `HMAC(secret, minute)` —
# a pure function of the clock, which any client could precompute without it. The rate is
# now a random walk stored in `bank_rates`, and state needs no secret to be unpredictable.


def validate_config() -> None:
    """Fail fast at startup instead of silently degrading to an insecure mode."""
    problems: list[str] = []

    if IS_PRODUCTION:
        if not BOT_TOKEN:
            problems.append("BOT_TOKEN is required in production: initData cannot be verified without it")
        if DEV_AUTH:
            problems.append("DEV_AUTH must be disabled in production: it lets any client impersonate any player")
        if not TELEGRAM_WEBHOOK_SECRET:
            problems.append("TELEGRAM_WEBHOOK_SECRET is required in production: Stars payments cannot be trusted without it")

    if INIT_DATA_MAX_AGE_SECONDS <= 0:
        problems.append("INIT_DATA_MAX_AGE_SECONDS must be positive")

    if SOCIAL_REWARD_AMOUNT <= 0:
        problems.append("SOCIAL_REWARD_AMOUNT must be positive")

    if problems:
        raise RuntimeError("Invalid configuration:\n  - " + "\n  - ".join(problems))
