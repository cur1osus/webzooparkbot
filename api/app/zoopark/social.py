from __future__ import annotations

import random
import string

from fastapi import HTTPException
from pydantic import BaseModel

from api.app.zoopark.profile import get_user
from api.app.zoopark.runtime import get_db


class ClanCreateBody(BaseModel):
    name: str
    spec: str | None = None


class ClanRequestBody(BaseModel):
    clan_id: int


class TransferCreateBody(BaseModel):
    total_rub: float
    max_claims: int


def api_top(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.id_user, u.nickname,
                    COALESCE(SUM(CAST(ai.income AS SIGNED) * CAST(a.quantity AS SIGNED)), 0) AS income
                FROM users u
                LEFT JOIN animals a ON a.user_id=u.id AND a.quantity>0
                LEFT JOIN animals_info ai ON ai.id=a.animal_info_id
                GROUP BY u.id
                ORDER BY income DESC
                LIMIT 20
                """
            )
            rows = cur.fetchall()
            cur.execute("SELECT id FROM users WHERE id_user=%s", (tg_id,))
            me = cur.fetchone()
            me_id = me["id"] if me else None

            entries: list[dict] = []
            my_rank = None
            for index, row in enumerate(rows):
                is_me = row["id"] == me_id
                if is_me:
                    my_rank = index + 1
                entries.append(
                    {
                        "rank": index + 1,
                        "tg_id": int(row["id_user"]),
                        "nickname": row["nickname"] or "—",
                        "income_rub_per_min": int(row["income"]),
                        "name_color": None,
                        "is_me": is_me,
                    }
                )
        return {"entries": entries, "my_rank": my_rank}
    finally:
        db.close()


def api_clan_list(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id_user=%s", (tg_id,))
            me = cur.fetchone()
            my_unity = me["unity_id"] if me else None
            my_user_id = me["id"] if me else None

            cur.execute(
                """
                SELECT c.idpk, c.name, c.level, c.owner_id,
                    COUNT(u2.id) AS member_count,
                    u3.nickname AS owner_nickname
                FROM unity c
                LEFT JOIN users u2 ON u2.unity_id=c.idpk
                LEFT JOIN users u3 ON u3.id=c.owner_id
                GROUP BY c.idpk ORDER BY c.level DESC LIMIT 20
                """
            )
            clans = cur.fetchall()

            my_clan = None
            my_role = None
            clan_list = []
            for clan in clans:
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
    finally:
        db.close()


def api_clan_create(
    tg_id: int,
    body: ClanCreateBody,
):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            if user["unity_id"]:
                raise HTTPException(400, "Ты уже в клане")

            name = body.name.strip()
            if not (1 <= len(name) <= 20):
                raise HTTPException(400, "Название 1-20 символов")
            if int(user["usd"]) < 1:
                raise HTTPException(400, "Нужен $1 для создания клана")

            cur.execute("SELECT idpk FROM unity WHERE name=%s", (name,))
            if cur.fetchone():
                raise HTTPException(400, "Клан уже существует")

            clan_id = random.randint(100000, 999999)
            cur.execute("INSERT INTO unity (id, name, level, owner_id) VALUES (%s,%s,1,%s)", (clan_id, name, user["id"]))
            idpk = cur.lastrowid
            cur.execute("UPDATE users SET unity_id=%s, usd=usd-1 WHERE id=%s", (idpk, user["id"]))
        db.commit()
        return {"ok": True, "message": f"Клан «{name}» создан!"}
    finally:
        db.close()


def api_clan_request(
    tg_id: int,
    body: ClanRequestBody,
):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            if user["unity_id"]:
                raise HTTPException(400, "Ты уже в клане")

            cur.execute("SELECT idpk, name FROM unity WHERE idpk=%s", (body.clan_id,))
            clan = cur.fetchone()
            if not clan:
                raise HTTPException(404, "Клан не найден")

            cur.execute("UPDATE users SET unity_id=%s WHERE id=%s", (body.clan_id, user["id"]))
        db.commit()
        return {"ok": True, "message": f"Вступил в клан «{clan['name']}»"}
    finally:
        db.close()


def api_clan_leave(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            if not user["unity_id"]:
                raise HTTPException(400, "Ты не в клане")

            user_id = user["id"]
            unity_id = user["unity_id"]
            cur.execute("SELECT owner_id FROM unity WHERE idpk=%s", (unity_id,))
            clan = cur.fetchone()
            cur.execute("UPDATE users SET unity_id=NULL WHERE id=%s", (user_id,))
            if clan and clan["owner_id"] == user_id:
                cur.execute("UPDATE users SET unity_id=NULL WHERE unity_id=%s", (unity_id,))
                cur.execute("DELETE FROM unity WHERE idpk=%s", (unity_id,))
        db.commit()
        return {"ok": True, "message": "Покинул клан"}
    finally:
        db.close()


def api_referrals(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")
            cur.execute(
                "SELECT u.nickname FROM referrals r JOIN users u ON u.id=r.referral_id WHERE r.user_id=%s",
                (user["id"],),
            )
            referred = [row["nickname"] or "—" for row in cur.fetchall()]
        return {"code": str(tg_id), "total": len(referred), "reward_usd_per_ref": 1, "referred": referred}
    finally:
        db.close()


def api_transfers_create(
    tg_id: int,
    body: TransferCreateBody,
):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                raise HTTPException(404, "Нет игрока")

            total = int(body.total_rub)
            max_claims = max(1, body.max_claims)
            if int(user["rub"]) < total:
                raise HTTPException(400, "Недостаточно рублей")

            rub_per_claim = total // max_claims
            if rub_per_claim < 1:
                raise HTTPException(400, "Слишком малая сумма")

            key = "".join(random.choices(string.ascii_letters + string.digits, k=16))
            cur.execute(
                "INSERT INTO transfer_links (link_key, creator_id, total_amount, rub_per_claim, max_claims) VALUES (%s,%s,%s,%s,%s)",
                (key, user["id"], total, rub_per_claim, max_claims),
            )
            cur.execute("UPDATE users SET rub=rub-%s WHERE id=%s", (total, user["id"]))
        db.commit()
        return {"key": key}
    finally:
        db.close()


def api_my_transfers(tg_id: int):
    db = get_db()
    try:
        with db.cursor() as cur:
            user = get_user(cur, tg_id)
            if not user:
                return {"transfers": []}

            cur.execute("SELECT * FROM transfer_links WHERE creator_id=%s ORDER BY created_at DESC LIMIT 20", (user["id"],))
            rows = cur.fetchall()
        return {
            "transfers": [
                {
                    "key": row["link_key"],
                    "total_rub": int(row["total_amount"]),
                    "rub_per_claim": int(row["rub_per_claim"]),
                    "max_claims": int(row["max_claims"]),
                    "claims": int(row["claims"]),
                    "active": bool(row["active"]),
                    "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
                }
                for row in rows
            ]
        }
    finally:
        db.close()
