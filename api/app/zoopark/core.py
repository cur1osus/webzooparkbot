from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from api.app.core.config import BOT_USERNAME
from api.app.db.connection import get_session
from api.app.db.models import User
from api.app.schemas.core import RegisterBody, SavePayload
from api.app.zoopark.income import sync_passive_balance
from api.app.zoopark.profile import build_state, get_user
from api.app.zoopark.season import ensure_player_season


def health() -> dict:
    return {"ok": True}


def me(tg_id: int) -> dict:
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        user, income, _expenses = sync_passive_balance(session, user)
        result = build_state(session, user, income)
        session.commit()
        return result


def save(tg_id: int, body: SavePayload) -> dict:
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            return {"ok": False, "rub": 0, "usd": 0, "paw_coins": 0, "balance_seq": 0, "data_version": 0}
        pre_sync_balance_seq = user.balance_seq or 0
        pre_sync_data_version = user.data_version or 0
        user, _income, _expenses = sync_passive_balance(session, user)
        current_usd = user.usd
        current_paw_coins = user.paw_coins

        if body.balance_seq >= pre_sync_balance_seq:
            current_usd = int(body.usd)
            current_paw_coins = int(body.paw_coins)
            user.usd = current_usd
            user.paw_coins = current_paw_coins

        if body.data_version >= pre_sync_data_version:
            user.data_version = max(user.data_version or 0, int(body.data_version))

        session.commit()
        return {
            "ok": True,
            "rub": user.rub,
            "usd": current_usd,
            "paw_coins": current_paw_coins,
            "balance_seq": user.balance_seq or 0,
            "data_version": user.data_version or 0,
        }


def register(tg_id: int, body: RegisterBody) -> dict:
    nickname = body.nickname.strip()
    if not (1 <= len(nickname) <= 20):
        raise HTTPException(400, "Никнейм 1-20 символов")
    with get_session() as session:
        if get_user(session, tg_id):
            raise HTTPException(400, "Уже зарегистрирован")
        if session.query(User).filter(User.nickname == nickname).first():
            raise HTTPException(400, "Никнейм занят")
        now = datetime.now(timezone.utc)
        user = User(id_user=tg_id, nickname=nickname, date_reg=now, paw_coins=0, rub=0, usd=1, sub_on_chat=0, sub_on_channel=0, bonus=1)
        session.add(user)
        session.flush()
        ensure_player_season(session, user)
        session.commit()
        gs = build_state(session, user, 0)
        return {"ok": True, "game_state": gs}


def config() -> dict:
    return {"bot_username": BOT_USERNAME}
