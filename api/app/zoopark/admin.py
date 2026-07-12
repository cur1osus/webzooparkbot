"""Owner-only operational views for the Mini App admin panel."""

from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from api.app.core.config import ADMIN_TG_IDS
from api.app.db.connection import get_session
from api.app.db.models import Animal, BankRate, LedgerEntry, Player, Treasury, utcnow
from api.app.schemas.admin import AdminGrantBody
from api.app.zoopark import ledger
from api.app.zoopark.income import alive_clause
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
            "players_list": [_player_payload(player, animal_counts.get(player.id, 0)) for player in players],
        }


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
