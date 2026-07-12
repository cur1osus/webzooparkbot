"""Auth is the outer wall: a bug here makes every other check decorative."""

from __future__ import annotations

import hashlib
import hmac
import importlib
import json
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from fastapi import HTTPException

BOT_TOKEN = "123456:TEST-TOKEN"


def _sign_init_data(user: dict, auth_date: int | None = None) -> str:
    params = {
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAF",
    }
    data_check = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


class AuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth_module = importlib.import_module("api.app.core.auth")

    def _parse(self, init_data: str = "", dev_id: str = "", **overrides):
        defaults = {"BOT_TOKEN": BOT_TOKEN, "DEV_AUTH": False, "INIT_DATA_MAX_AGE_SECONDS": 86400}
        defaults.update(overrides)
        with patch.multiple(self.auth_module, **defaults):
            return self.auth_module.parse_tg_id(init_data, dev_id)

    def test_valid_init_data_yields_the_user_id(self) -> None:
        self.assertEqual(self._parse(_sign_init_data({"id": 4242})), 4242)

    def test_dev_header_is_rejected_unless_dev_auth_is_on(self) -> None:
        """C-2: this header used to impersonate any player with no signature at all."""
        with self.assertRaises(HTTPException) as raised:
            self._parse(dev_id="4242")
        self.assertEqual(raised.exception.status_code, 401)

    def test_dev_header_works_when_dev_auth_is_on(self) -> None:
        self.assertEqual(self._parse(dev_id="4242", DEV_AUTH=True), 4242)

    def test_missing_bot_token_refuses_instead_of_trusting_the_client(self) -> None:
        """C-2: an empty BOT_TOKEN used to silently accept unsigned initData."""
        with self.assertRaises(HTTPException) as raised:
            self._parse(_sign_init_data({"id": 4242}), BOT_TOKEN="")
        self.assertEqual(raised.exception.status_code, 503)

    def test_tampered_signature_is_rejected(self) -> None:
        init_data = _sign_init_data({"id": 4242}).replace("4242", "1337")
        with self.assertRaises(HTTPException) as raised:
            self._parse(init_data)
        self.assertEqual(raised.exception.status_code, 401)

    def test_stale_init_data_is_rejected(self) -> None:
        """Captured initData must not stay valid forever."""
        stale = _sign_init_data({"id": 4242}, auth_date=int(time.time()) - 90_000)
        with self.assertRaises(HTTPException) as raised:
            self._parse(stale)
        self.assertEqual(raised.exception.status_code, 401)

    def test_name_with_a_plus_sign_can_authenticate(self) -> None:
        """I-3: unquote() before parse_qsl decoded values twice and broke these users."""
        self.assertEqual(self._parse(_sign_init_data({"id": 7, "first_name": "A+B"})), 7)

    def test_name_with_an_ampersand_can_authenticate(self) -> None:
        self.assertEqual(self._parse(_sign_init_data({"id": 8, "first_name": "A&B"})), 8)

    def test_name_with_a_percent_sign_can_authenticate(self) -> None:
        self.assertEqual(self._parse(_sign_init_data({"id": 9, "first_name": "100%"})), 9)


class ConfigTests(unittest.TestCase):
    def test_production_refuses_to_start_without_secrets(self) -> None:
        config = importlib.import_module("api.app.core.config")
        with patch.multiple(
            config,
            IS_PRODUCTION=True,
            BOT_TOKEN="",
            DEV_AUTH=True,
            TELEGRAM_WEBHOOK_SECRET="",
        ), self.assertRaises(RuntimeError) as raised:
            config.validate_config()

        message = str(raised.exception)
        self.assertIn("BOT_TOKEN", message)
        self.assertIn("DEV_AUTH", message)
        self.assertIn("TELEGRAM_WEBHOOK_SECRET", message)

    def test_production_with_secrets_validates(self) -> None:
        config = importlib.import_module("api.app.core.config")
        with patch.multiple(
            config,
            IS_PRODUCTION=True,
            BOT_TOKEN="token",
            DEV_AUTH=False,
            TELEGRAM_WEBHOOK_SECRET="hook",
        ):
            config.validate_config()

    def test_allowed_ids_parsing(self) -> None:
        config = importlib.import_module("api.app.core.config")
        with patch.dict("os.environ", {"ALLOWED_TG_IDS": "1,2, 3"}):
            self.assertEqual(config._env_allowed_ids("ALLOWED_TG_IDS", ""), {1, 2, 3})
        with patch.dict("os.environ", {"ALLOWED_TG_IDS": "*"}):
            self.assertIsNone(config._env_allowed_ids("ALLOWED_TG_IDS", ""))


if __name__ == "__main__":
    unittest.main()
