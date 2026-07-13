from unittest.mock import patch

from api.app.zoopark import core


def test_config_uses_username_returned_by_telegram():
    with patch.object(
        core,
        "call_bot_api",
        return_value={"ok": True, "result": {"username": "@Zoo_Park_bot"}},
    ) as call:
        assert core.config() == {"bot_username": "Zoo_Park_bot"}

    call.assert_called_once_with("getMe", {})
