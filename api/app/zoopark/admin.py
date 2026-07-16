"""Owner-only operational views for the Mini App admin panel."""

from __future__ import annotations

import base64
import binascii
import re
import secrets
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select

from api.app.core.config import ADMIN_TG_IDS
from api.app.db.connection import get_session
from api.app.db.models import (
    Animal,
    BankRate,
    CustomAchievement,
    CustomAchievementRecipient,
    LedgerEntry,
    Player,
    Treasury,
    utcnow,
)
from api.app.schemas.admin import AdminCreateAchievementBody, AdminGrantBody, AdminMaintenanceBody
from api.app.zoopark import ledger
from api.app.zoopark.income import alive_clause
from api.app.zoopark import maintenance
from api.app.zoopark.profile import get_player


def require_admin(tg_id: int) -> None:
    if tg_id not in ADMIN_TG_IDS:
        raise HTTPException(403, "Недостаточно прав")


def _player_payload(player: Player, animals_count: int) -> dict:
    return {
        "id": player.id,
        "tg_id": player.telegram_id,
        "nickname": player.nickname,
        "username": player.username,
        "status": player.status,
        "registered_at": player.registered_at.isoformat(),
        "last_seen_at": player.last_seen_at.isoformat() if player.last_seen_at else None,
        "rub": player.balance_rub,
        "usd": player.balance_usd,
        "paw": player.balance_paw,
        "animals_count": animals_count,
        "income_rub_per_min": player.income_rub_per_min,
        "upkeep_rub_per_min": player.upkeep_rub_per_min,
        "net_income_rub_per_min": player.income_rub_per_min - player.upkeep_rub_per_min,
    }


def overview(tg_id: int, search: str = "") -> dict:
    require_admin(tg_id)
    now = utcnow()
    query = search.strip()

    with get_session() as session:
        player_count = int(session.scalar(select(func.count(Player.id))) or 0)
        active_count = int(session.scalar(select(func.count(Player.id)).where(Player.status == "active")) or 0)
        banned_count = int(session.scalar(select(func.count(Player.id)).where(Player.status == "banned")) or 0)
        online_count = int(
            session.scalar(
                select(func.count(Player.id)).where(
                    Player.status == "active",
                    Player.last_seen_at >= now - timedelta(minutes=15),
                )
            )
            or 0
        )
        animal_count = int(session.scalar(select(func.count(Animal.id)).where(alive_clause(now))) or 0)
        totals = {
            "rub": int(session.scalar(select(func.sum(Player.balance_rub))) or 0),
            "usd": int(session.scalar(select(func.sum(Player.balance_usd))) or 0),
            "paw": int(session.scalar(select(func.sum(Player.balance_paw))) or 0),
        }
        treasury = {
            currency: int(session.scalar(select(Treasury.balance).where(Treasury.currency == currency)) or 0)
            for currency in ("rub", "usd", "paw")
        }
        rate = session.scalars(select(BankRate).order_by(BankRate.period.desc()).limit(1)).first()
        ledger_today = int(
            session.scalar(
                select(func.count(LedgerEntry.id)).where(
                    LedgerEntry.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
                )
            )
            or 0
        )

        stmt = select(Player).order_by(Player.last_seen_at.desc(), Player.id.desc()).limit(50)
        if query:
            pattern = f"%{query}%"
            if query.isdigit():
                stmt = stmt.where(or_(Player.telegram_id == int(query), Player.nickname.ilike(pattern)))
            else:
                stmt = stmt.where(or_(Player.nickname.ilike(pattern), Player.username.ilike(pattern)))
        players = session.scalars(stmt).all()
        player_ids = [player.id for player in players]
        animal_counts: dict[int, int] = {}
        if player_ids:
            rows = session.execute(
                select(Animal.player_id, func.count(Animal.id))
                .where(Animal.player_id.in_(player_ids), alive_clause(now))
                .group_by(Animal.player_id)
            ).all()
            animal_counts = {int(player_id): int(count) for player_id, count in rows}

        custom_achievements = session.execute(
            select(
                CustomAchievement.id,
                CustomAchievement.title,
                CustomAchievement.description,
                CustomAchievement.audience,
                CustomAchievement.created_at,
                func.count(CustomAchievementRecipient.player_id),
            )
            .outerjoin(
                CustomAchievementRecipient,
                CustomAchievementRecipient.achievement_id == CustomAchievement.id,
            )
            .group_by(CustomAchievement.id)
            .order_by(CustomAchievement.created_at.desc(), CustomAchievement.id.desc())
        ).all()

        return {
            "generated_at": now.isoformat(),
            "stats": {
                "players": player_count,
                "active_players": active_count,
                "banned_players": banned_count,
                "online_players": online_count,
                "animals": animal_count,
                "ledger_entries_today": ledger_today,
            },
            "balances": totals,
            "treasury": treasury,
            "bank_rate": rate.rate_rub_per_usd if rate else None,
            "maintenance": maintenance.status(session, now),
            "players_list": [_player_payload(player, animal_counts.get(player.id, 0)) for player in players],
            "custom_achievements": [
                {
                    "id": achievement_id,
                    "title": title,
                    "description": description,
                    "audience": audience,
                    "recipient_count": int(recipient_count),
                    "image_url": f"/api/achievements/{achievement_id}/image",
                    "created_at": created_at.isoformat(),
                }
                for achievement_id, title, description, audience, created_at, recipient_count in custom_achievements
            ],
        }


_IMAGE_DATA_RE = re.compile(r"^data:(image/(?:jpeg|png|webp|gif));base64,([A-Za-z0-9+/=\s]+)$")
_MAX_IMAGE_BYTES = 1_500_000


def create_custom_achievement(admin_tg_id: int, body: AdminCreateAchievementBody) -> dict:
    require_admin(admin_tg_id)
    title = body.title.strip()
    description = body.description.strip()
    if not title or not description:
        raise HTTPException(400, "Заполни название и описание")

    match = _IMAGE_DATA_RE.fullmatch(body.image_data.strip())
    if not match:
        raise HTTPException(400, "Загрузи изображение в формате JPG, PNG, WEBP или GIF")
    image_mime, encoded = match.groups()
    try:
        image_data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(400, "Изображение повреждено") from exc
    if not image_data or len(image_data) > _MAX_IMAGE_BYTES:
        raise HTTPException(400, "Изображение должно весить не больше 1,5 МБ")

    with get_session() as session:
        player_ids = set(
            session.scalars(select(Player.id).where(Player.telegram_id.in_(body.player_tg_ids))).all()
        )
        if body.audience == "selected" and len(player_ids) != len(set(body.player_tg_ids)):
            raise HTTPException(400, "Один из выбранных аккаунтов не найден")
        if body.audience == "selected" and not player_ids:
            raise HTTPException(400, "Выбери хотя бы одного получателя")

        achievement = CustomAchievement(
            id=f"custom_{secrets.token_hex(16)}",
            title=title,
            description=description,
            audience=body.audience,
            image_data=image_data,
            image_mime=image_mime,
        )
        session.add(achievement)
        session.flush()
        session.add_all(
            CustomAchievementRecipient(achievement_id=achievement.id, player_id=player_id)
            for player_id in player_ids
        )
        session.commit()
        return {
            "ok": True,
            "id": achievement.id,
            "image_url": f"/api/achievements/{achievement.id}/image",
        }


def custom_achievement_image(achievement_id: str):
    with get_session() as session:
        achievement = session.get(CustomAchievement, achievement_id)
        if achievement is None:
            raise HTTPException(404, "Изображение не найдено")
        return achievement.image_data, achievement.image_mime


def delete_custom_achievement(admin_tg_id: int, achievement_id: str) -> dict:
    require_admin(admin_tg_id)
    with get_session() as session:
        achievement = session.get(CustomAchievement, achievement_id, with_for_update=True)
        if achievement is None:
            raise HTTPException(404, "Медаль не найдена")

        # A profile avatar is stored as a compact achievement:<id> reference. Clear it
        # before removing the catalogue row so nobody is left with a broken avatar.
        players = session.scalars(
            select(Player).where(Player.profile_emoji == f"achievement:{achievement_id}").with_for_update()
        ).all()
        for player in players:
            player.profile_emoji = None
        session.execute(
            delete(CustomAchievementRecipient).where(
                CustomAchievementRecipient.achievement_id == achievement_id
            )
        )
        session.delete(achievement)
        session.commit()
        return {"ok": True, "id": achievement_id}


def grant_currency(admin_tg_id: int, telegram_id: int, body: AdminGrantBody) -> dict:
    require_admin(admin_tg_id)
    with get_session() as session:
        player = get_player(session, telegram_id, for_update=True)
        if player is None:
            raise HTTPException(404, "Игрок не найден")
        new_balance = ledger.grant(session, player, body.currency, body.amount, "admin_grant")  # type: ignore[arg-type]
        session.commit()
        return {"ok": True, "tg_id": telegram_id, "currency": body.currency, "new_balance": new_balance}


def set_player_status(admin_tg_id: int, telegram_id: int, status: str) -> dict:
    require_admin(admin_tg_id)
    if telegram_id in ADMIN_TG_IDS and status == "banned":
        raise HTTPException(400, "Нельзя заблокировать администратора")
    with get_session() as session:
        player = session.scalars(select(Player).where(Player.telegram_id == telegram_id).with_for_update()).first()
        if player is None:
            raise HTTPException(404, "Игрок не найден")
        player.status = status
        session.commit()
        return {"ok": True, "tg_id": telegram_id, "status": status}


def get_maintenance(admin_tg_id: int) -> dict:
    require_admin(admin_tg_id)
    with get_session() as session:
        return maintenance.status(session)


def start_maintenance(admin_tg_id: int, body: AdminMaintenanceBody) -> dict:
    require_admin(admin_tg_id)
    with get_session() as session:
        result = maintenance.start(session, body.duration_minutes, body.message)
        session.commit()
        return result


def end_maintenance(admin_tg_id: int) -> dict:
    require_admin(admin_tg_id)
    with get_session() as session:
        result = maintenance.end(session)
        session.commit()
        return result
