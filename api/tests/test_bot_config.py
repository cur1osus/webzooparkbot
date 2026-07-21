from unittest.mock import patch

import pytest

from api.app.zoopark import core


@pytest.fixture(autouse=True)
def _cold_cache(monkeypatch):
    """Every test here starts having never asked Telegram. Without this they depend on
    whichever test ran first, which is how the CI run and the local run disagreed."""
    monkeypatch.setattr(core, "_bot_username_cache", None)
    monkeypatch.setattr(core, "_bot_username_cache_at", None)


def test_config_uses_username_returned_by_telegram():
    with patch.object(
        core,
        "call_bot_api",
        return_value={"ok": True, "result": {"username": "@Zoo_Park_bot"}},
    ) as call:
        assert core.config() == {"bot_username": "Zoo_Park_bot"}

    call.assert_called_once_with("getMe", {})


def test_a_freshly_booted_host_still_asks_telegram(monkeypatch):
    """`time.monotonic()` is uptime on Linux, so shortly after a boot it is a small number.
    With the "last fetched" marker initialised to 0.0, `now - 0.0` fell inside the five
    minute TTL and the never-populated cache was served as if it were fresh — production
    answered `bot_username: None` for five minutes after every restart. No developer
    machine, with days of uptime, could reproduce it."""
    monkeypatch.setattr(core.time, "monotonic", lambda: 12.0)  # 12 секунд после загрузки

    with patch.object(
        core,
        "call_bot_api",
        return_value={"ok": True, "result": {"username": "@Zoo_Park_bot"}},
    ) as call:
        assert core.config() == {"bot_username": "Zoo_Park_bot"}

    call.assert_called_once_with("getMe", {})
