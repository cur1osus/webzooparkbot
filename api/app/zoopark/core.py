"""Registration and the state the client boots from.

There is no `POST /api/save`. It carried a single field, `data_version`, which the server
stored and handed back and nobody ever read; currencies have been server-authoritative
since long before that. What the client actually needed from it — a fresh balance — is
what `GET /api/me` returns.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.core.config import BOT_USERNAME
from api.app.db.connection import get_session
from api.app.db.models import Player, PlayerCosmetic, utcnow
from api.app.schemas.core import NicknameColorBody, RegisterBody
from api.app.zoopark import ledger
from api.app.zoopark.catalog import NICKNAME_COLORS, REFERRAL_SIGNUP_REWARD_USD
from api.app.zoopark.income import sync_player_income
from api.app.zoopark.progression import ensure_first_locality
from api.app.zoopark.profile import build_state, get_player
from api.app.zoopark.season import ensure_player_season

logger = logging.getLogger(__name__)


def health() -> dict:
    return {"ok": True}


def config() -> dict:
    return {"bot_username": BOT_USERNAME}


def me(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Пользователь не найден")
        sync_player_income(session, player)
        player.last_seen_at = utcnow()
        state = build_state(session, player)
        session.commit()
        return state


def set_nickname_color(tg_id: int, body: NicknameColorBody) -> dict:
    if body.color not in NICKNAME_COLORS:
        raise HTTPException(400, "Неизвестный цвет ника")

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Пользователь не найден")
        if body.color != "ivory" and session.get(PlayerCosmetic, (player.id, body.color)) is None:
            raise HTTPException(400, "Сначала открой этот цвет за PawCoins")
        player.nickname_color = body.color
        session.commit()
        return {"ok": True, "nickname_color": player.nickname_color}


def buy_nickname_color(tg_id: int, color: str) -> dict:
    color_def = NICKNAME_COLORS.get(color)
    if color_def is None:
        raise HTTPException(404, "Цвет не найден")

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Пользователь не найден")

        cosmetic = session.get(PlayerCosmetic, (player.id, color))
        if cosmetic is None and color_def["price_paw"] > 0:
            ledger.spend(session, player, "paw", color_def["price_paw"], "cosmetic_purchase")
            session.add(PlayerCosmetic(player_id=player.id, cosmetic_id=color))
        player.nickname_color = color
        session.commit()
        return {
            "ok": True,
            "nickname_color": player.nickname_color,
            "new_paw_coins": ledger.balance(player, "paw"),
        }


def _parse_ref_code(raw: str | None) -> int | None:
    if not raw:
        return None
    code = raw.strip()
    # Telegram start params are often prefixed, e.g. "ref_123456".
    if code.startswith("ref_"):
        code = code[4:]
    try:
        return int(code)
    except ValueError:
        return None


def _link_referrer(session: Session, new_player: Player, referrer_tg_id: int) -> None:
    if referrer_tg_id == new_player.telegram_id:
        return
    referrer = get_player(session, referrer_tg_id, for_update=True)
    if referrer is None:
        logger.info("Referral code %s does not match any player", referrer_tg_id)
        return
    new_player.referred_by_id = referrer.id
    ledger.grant(
        session, referrer, "usd", REFERRAL_SIGNUP_REWARD_USD, "referral_signup",
        ref_table="players", ref_id=new_player.id,
    )


def register(tg_id: int, body: RegisterBody) -> dict:
    nickname = body.nickname.strip()
    if not (1 <= len(nickname) <= 32):
        raise HTTPException(400, "Никнейм 1–32 символа")

    with get_session() as session:
        if get_player(session, tg_id) is not None:
            raise HTTPException(400, "Уже зарегистрирован")

        player = Player(telegram_id=tg_id, nickname=nickname)
        session.add(player)
        try:
            session.flush()
        except IntegrityError as exc:
            # `players.nickname` and `players.telegram_id` are both unique in the schema,
            # so the racy `SELECT … WHERE nickname = ?` this used to rely on is gone.
            session.rollback()
            raise HTTPException(400, _registration_conflict(exc, tg_id, nickname)) from exc

        ledger.grant(session, player, "usd", 1, "register")

        referrer_tg_id = _parse_ref_code(body.ref_code)
        if referrer_tg_id is not None:
            _link_referrer(session, player, referrer_tg_id)

        season = ensure_player_season(session, player)
        # GDD §5: the first locality is free. Granted here rather than lazily on the first
        # GET, which left `/api/me` reporting `localities_count: 0` until you opened that
        # screen.
        ensure_first_locality(session, player.id, season.id)
        sync_player_income(session, player)
        state = build_state(session, player)
        session.commit()
        return {"ok": True, "game_state": state}


def _registration_conflict(exc: IntegrityError, tg_id: int, nickname: str) -> str:
    """Turn the unique-key violation back into the message the player needs."""
    detail = str(exc.orig).lower()
    if "nickname" in detail:
        return "Никнейм занят"
    if "telegram_id" in detail:
        return "Уже зарегистрирован"
    logger.warning("Unrecognised registration conflict for %s/%s: %s", tg_id, nickname, exc)
    return "Не удалось зарегистрироваться"
