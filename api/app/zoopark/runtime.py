from __future__ import annotations

import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl, unquote

import pymysql
import pymysql.cursors
from fastapi import HTTPException


DB_CFG = dict(
    host="127.0.0.1",
    user=os.getenv("DB_USER", "admin_zoopark"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "zoopark"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "ZooParkBot")

ALLOWED_TG_IDS: set[int] | None = {474701274}
CLOSED_MSG = "🚧 Игра в разработке. Скоро открытие — следи за обновлениями!"


def get_db():
    return pymysql.connect(**DB_CFG)


def parse_tg_id(x_init_data: str, x_dev_user_id: str) -> int:
    if x_dev_user_id:
        try:
            return int(x_dev_user_id)
        except ValueError as exc:
            raise HTTPException(401, "Bad dev user id") from exc

    if x_init_data:
        if not BOT_TOKEN:
            try:
                params = dict(parse_qsl(unquote(x_init_data), keep_blank_values=True))
                user = json.loads(params.get("user", "{}"))
                if uid := user.get("id"):
                    return int(uid)
            except Exception:
                pass
        else:
            try:
                params = dict(parse_qsl(unquote(x_init_data), keep_blank_values=True))
                hash_val = params.pop("hash", "")
                data_check = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
                secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
                calc = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
                if hmac.compare_digest(calc, hash_val):
                    user = json.loads(params.get("user", "{}"))
                    if uid := user.get("id"):
                        return int(uid)
            except Exception:
                pass

    raise HTTPException(401, "Unauthorized")


def auth(x_init_data: str, x_dev_user_id: str) -> int:
    tg_id = parse_tg_id(x_init_data, x_dev_user_id)
    if ALLOWED_TG_IDS is not None and tg_id not in ALLOWED_TG_IDS:
        raise HTTPException(403, CLOSED_MSG)
    return tg_id
