from __future__ import annotations

import random
import string

from fastapi import HTTPException
from sqlalchemy import text

from api.app.db.connection import get_session
from api.app.db.models import Referral, TransferLink, Unity, User
from api.app.schemas.social import ClanCreateBody, ClanRequestBody, TransferCreateBody
from api.app.zoopark.income import calc_pack_income, sync_passive_balance
from api.app.zoopark.profile import get_user
from api.app.zoopark.season import active_season


def api_top(tg_id: int):
    with get_session() as session:
        season = active_season(session)
        users = session.query(User).all()

        me_user = session.query(User).filter(User.id_user == tg_id).first()
        me_id = me_user.id if me_user else None
        ranked = sorted(
            (
                {"id": user.id, "id_user": user.id_user, "nickname": user.nickname, "income": calc_pack_income(session, user.id, season.id)}
                for user in users
            ),
            key=lambda row: row["income"],
            reverse=True,
        )[:20]

        entries: list[dict] = []
        my_rank = None
        for index, row in enumerate(ranked):
            is_me = row["id"] == me_id
            if is_me:
                my_rank = index + 1
            entries.append({
                "rank": index + 1,
                "tg_id": int(row["id_user"]),
                "nickname": row["nickname"] or "—",
                "income_rub_per_min": int(row["income"]),
                "name_color": None,
                "is_me": is_me,
            })
        return {"entries": entries, "my_rank": my_rank}


def api_clan_list(tg_id: int):
    with get_session() as session:
        me_user = session.query(User).filter(User.id_user == tg_id).first()
        my_unity = me_user.unity_id if me_user else None
        my_user_id = me_user.id if me_user else None

        rows = session.execute(text(
            """
            SELECT c.idpk, c.name, c.level, c.owner_id,
                COUNT(u2.id) AS member_count,
                u3.nickname AS owner_nickname
            FROM zoopark_unity c
            LEFT JOIN zoopark_users u2 ON u2.unity_id=c.idpk
            LEFT JOIN zoopark_users u3 ON u3.id=c.owner_id
            GROUP BY c.idpk ORDER BY c.level DESC LIMIT 20
            """
        )).mappings().all()

        my_clan = None
        my_role = None
        clan_list = []
        for clan in rows:
            entry = {
                "idpk": clan["idpk"],
                "name": clan["name"],
                "level": int(clan["level"]),
                "member_count": int(clan["member_count"]),
                "specialty": None,
                "owner_nickname": clan["owner_nickname"] or "—",
            }
            clan_list.append(entry)
            if my_unity and clan["idpk"] == my_unity:
                my_clan = entry
                my_role = "owner" if my_user_id and clan["owner_id"] == my_user_id else "member"
        return {"clans": clan_list, "my_clan": my_clan, "my_role": my_role}


def api_clan_create(tg_id: int, body: ClanCreateBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        if user.unity_id:
            raise HTTPException(400, "Ты уже в клане")

        name = body.name.strip()
        if not (1 <= len(name) <= 20):
            raise HTTPException(400, "Название 1-20 символов")
        if user.usd < 1:
            raise HTTPException(400, "Нужен $1 для создания клана")
        if session.query(Unity).filter(Unity.name == name).first():
            raise HTTPException(400, "Клан уже существует")

        clan_id = random.randint(100000, 999999)
        clan = Unity(id=clan_id, name=name, level=1, owner_id=user.id)
        session.add(clan)
        session.flush()
        user.unity_id = clan.idpk
        user.usd -= 1
        session.commit()
        return {"ok": True, "message": f"Клан «{name}» создан!"}


def api_clan_request(tg_id: int, body: ClanRequestBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        if user.unity_id:
            raise HTTPException(400, "Ты уже в клане")

        clan = session.get(Unity, body.clan_id)
        if not clan:
            raise HTTPException(404, "Клан не найден")

        user.unity_id = body.clan_id
        session.commit()
        return {"ok": True, "message": f"Вступил в клан «{clan.name}»"}


def api_clan_members(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        if not user.unity_id:
            raise HTTPException(400, "Ты не в клане")

        season = active_season(session)
        clan = session.get(Unity, user.unity_id)
        members = session.query(User).filter(User.unity_id == user.unity_id).all()

        result = []
        for m in members:
            income = calc_pack_income(session, m.id, season.id)
            result.append({
                "tg_id": int(m.id_user),
                "nickname": m.nickname or "—",
                "role": "owner" if clan and clan.owner_id == m.id else "member",
                "income_rub_per_min": int(income),
            })

        result.sort(key=lambda x: (x["role"] != "owner", -x["income_rub_per_min"]))
        return {"members": result}


def api_clan_leave(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        if not user.unity_id:
            raise HTTPException(400, "Ты не в клане")

        user_id = user.id
        unity_id = user.unity_id
        clan = session.get(Unity, unity_id)
        user.unity_id = None
        if clan and clan.owner_id == user_id:
            session.query(User).filter(User.unity_id == unity_id).update({"unity_id": None})
            session.delete(clan)
        session.commit()
        return {"ok": True, "message": "Покинул клан"}


def api_referrals(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        referred = [
            row.nickname or "—"
            for row in session.query(User.nickname)
            .join(Referral, User.id == Referral.referral_id)
            .filter(Referral.user_id == user.id)
            .all()
        ]
        return {"code": str(tg_id), "total": len(referred), "reward_usd_per_ref": 1, "referred": referred}


def api_transfers_create(tg_id: int, body: TransferCreateBody):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            raise HTTPException(404, "Нет игрока")
        user, _income, _expenses = sync_passive_balance(session, user)

        total = int(body.total_rub)
        max_claims = max(1, body.max_claims)
        if user.rub < total:
            raise HTTPException(400, "Недостаточно рублей")

        rub_per_claim = total // max_claims
        if rub_per_claim < 1:
            raise HTTPException(400, "Слишком малая сумма")

        key = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        from datetime import datetime, timezone
        link = TransferLink(
            link_key=key, creator_id=user.id, total_amount=total,
            rub_per_claim=rub_per_claim, max_claims=max_claims,
            created_at=datetime.now(timezone.utc),
        )
        session.add(link)
        user.rub -= total
        session.commit()
        return {"key": key}


def api_my_transfers(tg_id: int):
    with get_session() as session:
        user = get_user(session, tg_id)
        if not user:
            return {"transfers": []}

        rows = (
            session.query(TransferLink)
            .filter(TransferLink.creator_id == user.id)
            .order_by(TransferLink.created_at.desc())
            .limit(20)
            .all()
        )
        return {
            "transfers": [
                {
                    "key": row.link_key,
                    "total_rub": row.total_amount,
                    "rub_per_claim": row.rub_per_claim,
                    "max_claims": row.max_claims,
                    "claims": row.claims,
                    "active": bool(row.active),
                    "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else str(row.created_at),
                }
                for row in rows
            ]
        }
