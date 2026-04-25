from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import parse_qsl, unquote

from fastapi import HTTPException

from api.app.core.config import ALLOWED_TG_IDS, BOT_TOKEN, CLOSED_MSG


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
