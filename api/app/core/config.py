from __future__ import annotations

import os


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "ZooParkBot")

ALLOWED_TG_IDS: set[int] | None = {474701274}
CLOSED_MSG = "🚧 Игра в разработке. Скоро открытие — следи за обновлениями!"
