from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "INVALID_TOKEN")
    dev_mode: bool = os.getenv("DEV_MODE", "").lower() in {"1", "true", "yes"}
    db_url_override: str | None = os.getenv("DB_URL") or None
    db_host: str = os.getenv("DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_user: str = os.getenv("DB_USER", "zooparkbot")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_name: str = os.getenv("DB_NAME", "zooparkbot")
    app_timezone_offset_hours: int = int(os.getenv("APP_TIMEZONE_OFFSET_HOURS", "3"))

    @property
    def db_url(self) -> str:
        if self.db_url_override:
            return self.db_url_override
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
