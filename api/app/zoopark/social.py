"""Leaderboard, clans, referrals and money transfers.

The leaderboard reads `players.income_rub_per_min`, an indexed column kept current by
`income.sync_player_income`. It used to be a full scan of every player joined to every
animal, run twice for anyone outside the top twenty.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import Animal, Clan, ClanMember, Locality, Player, Transfer, TransferClaim, utcnow
from api.app.schemas.social import ClanCreateBody, ClanRequestBody, TransferCreateBody
from api.app.zoopark import ledger
from api.app.zoopark.catalog import (
    CLAN_CREATE_COST_USD,
    CLAN_MAX_MEMBERS,
    REFERRAL_NEW_PLAYER_REWARD_USD,
    REFERRAL_SIGNUP_REWARD_USD,
    TOP_LIMIT,
    TRANSFER_MAX_CLAIMS,
    TRANSFER_TTL_HOURS,
    SPECIES_BY_ID,
)
from api.app.zoopark import achievements as achievements_module
from api.app.zoopark.income import sync_player_income
from api.app.zoopark.profile import get_clan, get_player
from api.app.zoopark.season import active_season


# ─── Leaderboard ──────────────────────────────────────────────────────────────


def top(tg_id: int) -> dict:
    with get_session() as session:
        me = get_player(session, tg_id)
        my_id = me.id if me else None

        rows = session.scalars(
            select(Player)
            .where(Player.status == "active")
            .order_by(Player.income_rub_per_min.desc(), Player.id.asc())
            .limit(TOP_LIMIT)
        ).all()

        entries = []
        my_rank = None
        for index, player in enumerate(rows, start=1):
            is_me = player.id == my_id
            if is_me:
                my_rank = index
            entries.append(
                {
                    "rank": index,
                    "tg_id": player.telegram_id,
                    "nickname": player.nickname,
                    "nickname_color": player.nickname_color,
                    "profile_emoji": player.profile_emoji,
                    "profile_frame": player.profile_frame,
                    "profile_wallpaper": player.profile_wallpaper,
                    "income_rub_per_min": player.income_rub_per_min,
                    "is_me": is_me,
                }
            )

        if my_rank is None and me is not None:
            ahead = session.scalar(
                select(func.count(Player.id)).where(
                    Player.status == "active",
                    Player.income_rub_per_min > me.income_rub_per_min,
                )
            )
            my_rank = int(ahead or 0) + 1

        return {"entries": entries, "my_rank": my_rank}


def public_profile(viewer_tg_id: int, target_tg_id: int) -> dict:
    """Return the non-sensitive profile surface used by the leaderboard sheet."""
    with get_session() as session:
        viewer = get_player(session, viewer_tg_id)
        if not viewer:
            raise HTTPException(404, "Нет игрока")

        target = session.scalars(
            select(Player).where(Player.telegram_id == target_tg_id, Player.status == "active")
        ).first()
        if not target:
            raise HTTPException(404, "Игрок не найден")

        ahead = session.scalar(
            select(func.count(Player.id)).where(
                Player.status == "active",
                or_(
                    Player.income_rub_per_min > target.income_rub_per_min,
                    and_(
                        Player.income_rub_per_min == target.income_rub_per_min,
                        Player.id < target.id,
                    ),
                ),
            )
        )
        rank = int(ahead or 0) + 1

        season = active_season(session)
        animals = session.scalars(
            select(Animal).where(
                Animal.player_id == target.id,
                Animal.season_id == season.id,
                Animal.removed_at.is_(None),
                Animal.dies_at > utcnow(),
            )
        ).all()
        species_counts: dict[int, int] = {}
        for animal in animals:
            species_counts[animal.species_id] = species_counts.get(animal.species_id, 0) + 1

        species = [
            {
                "name": SPECIES_BY_ID[species_id]["name"],
                "emoji": SPECIES_BY_ID[species_id]["emoji"],
                "count": count,
            }
            for species_id, count in sorted(species_counts.items(), key=lambda item: (-item[1], item[0]))
            if species_id in SPECIES_BY_ID
        ]
        localities = session.scalars(
            select(Locality).where(Locality.player_id == target.id, Locality.season_id == season.id)
        ).all()
        achievements = achievements_module.list_achievements(session, target)

        return {
            "tg_id": target.telegram_id,
            "nickname": target.nickname,
            "nickname_color": target.nickname_color,
            "profile_emoji": target.profile_emoji,
            "profile_frame": target.profile_frame,
            "profile_wallpaper": target.profile_wallpaper,
            "rank": rank,
            "income_rub_per_min": target.income_rub_per_min,
            "upkeep_rub_per_min": target.upkeep_rub_per_min,
            "animals_count": len(animals),
            "species_count": len(species_counts),
            "localities_count": len(localities),
            "locality_levels": sum(int(locality.level) for locality in localities),
            "achievements_completed": sum(achievement["completed"] for achievement in achievements),
            "achievements_total": len(achievements),
            "vet_level": target.vet_level,
            "genetics_level": target.genetics_level,
            "registered_at": target.registered_at.isoformat(),
            "clan": get_clan(session, target.id),
            "species": species,
        }


# ─── Clans ────────────────────────────────────────────────────────────────────


def _member_counts(session: Session) -> dict[int, int]:
    rows = session.execute(
        select(ClanMember.clan_id, func.count(ClanMember.player_id)).group_by(ClanMember.clan_id)
    ).all()
    return {clan_id: int(count) for clan_id, count in rows}


def clan_list(tg_id: int) -> dict:
    with get_session() as session:
        me = get_player(session, tg_id)
        my_membership = (
            session.scalars(select(ClanMember).where(ClanMember.player_id == me.id)).first() if me else None
        )

        clans = session.scalars(select(Clan).order_by(Clan.level.desc(), Clan.id.asc()).limit(20)).all()
        counts = _member_counts(session)
        owners = {
            player.id: player.nickname
            for player in session.scalars(
                select(Player).where(Player.id.in_([clan.owner_id for clan in clans] or [0]))
            ).all()
        }

        payload = []
        my_clan = None
        for clan in clans:
            entry = {
                "id": clan.id,
                "name": clan.name,
                "level": clan.level,
                "member_count": counts.get(clan.id, 0),
                "owner_nickname": owners.get(clan.owner_id, "—"),
            }
            payload.append(entry)
            if my_membership and my_membership.clan_id == clan.id:
                my_clan = entry

        return {
            "clans": payload,
            "my_clan": my_clan,
            "my_role": my_membership.role if my_membership else None,
        }


def clan_create(tg_id: int, body: ClanCreateBody) -> dict:
    name = body.name.strip()
    if not (1 <= len(name) <= 32):
        raise HTTPException(400, "Название 1–32 символа")

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        if session.scalars(select(ClanMember).where(ClanMember.player_id == player.id)).first():
            raise HTTPException(400, "Ты уже в клане")

        ledger.spend(session, player, "usd", CLAN_CREATE_COST_USD, "clan_create")

        clan = Clan(name=name, owner_id=player.id)
        session.add(clan)
        try:
            session.flush()
        except IntegrityError as exc:
            raise HTTPException(400, "Клан с таким названием уже есть") from exc

        session.add(ClanMember(clan_id=clan.id, player_id=player.id, role="owner"))
        result = {"ok": True, "id": clan.id, "message": f"Клан «{name}» создан!", "new_usd": ledger.balance(player, "usd")}
        session.commit()
        return result


def clan_join(tg_id: int, body: ClanRequestBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        clan = session.get(Clan, body.clan_id, with_for_update=True)
        if not clan:
            raise HTTPException(404, "Клан не найден")

        members = session.scalar(select(func.count(ClanMember.player_id)).where(ClanMember.clan_id == clan.id)) or 0
        if members >= CLAN_MAX_MEMBERS:
            raise HTTPException(400, f"В клане уже {CLAN_MAX_MEMBERS} участников")

        session.add(ClanMember(clan_id=clan.id, player_id=player.id, role="member"))
        try:
            session.flush()
        except IntegrityError as exc:
            # `uq_clan_members_player`: one clan per player, enforced by the schema.
            raise HTTPException(400, "Ты уже в клане") from exc

        result = {"ok": True, "message": f"Вступил в клан «{clan.name}»"}
        session.commit()
        return result


def clan_members(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        membership = session.scalars(select(ClanMember).where(ClanMember.player_id == player.id)).first()
        if membership is None:
            raise HTTPException(400, "Ты не в клане")

        rows = session.execute(
            select(Player, ClanMember.role)
            .join(ClanMember, ClanMember.player_id == Player.id)
            .where(ClanMember.clan_id == membership.clan_id)
            .order_by(Player.income_rub_per_min.desc())
        ).all()

        members = [
            {
                "tg_id": member.telegram_id,
                "nickname": member.nickname,
                "role": role,
                "income_rub_per_min": member.income_rub_per_min,
            }
            for member, role in rows
        ]
        members.sort(key=lambda entry: (entry["role"] != "owner", -int(entry["income_rub_per_min"])))
        return {"members": members}


def clan_leave(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        membership = session.scalars(
            select(ClanMember).where(ClanMember.player_id == player.id).with_for_update()
        ).first()
        if membership is None:
            raise HTTPException(400, "Ты не в клане")

        clan = session.get(Clan, membership.clan_id, with_for_update=True)
        session.delete(membership)
        # The owner leaving dissolves the clan; `ondelete=CASCADE` clears the memberships.
        if clan is not None and clan.owner_id == player.id:
            session.delete(clan)

        session.commit()
        return {"ok": True, "message": "Покинул клан"}


# ─── Referrals ────────────────────────────────────────────────────────────────


def referrals(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        referred = session.scalars(
            select(Player.nickname).where(Player.referred_by_id == player.id).order_by(Player.registered_at.asc())
        ).all()
        return {
            "code": str(tg_id),
            "total": len(referred),
            "signup_reward_usd": REFERRAL_SIGNUP_REWARD_USD,
            "new_player_reward_usd": REFERRAL_NEW_PLAYER_REWARD_USD,
            "referred": list(referred),
        }


# ─── Transfers ────────────────────────────────────────────────────────────────


def transfers_create(tg_id: int, body: TransferCreateBody) -> dict:
    if not (1 <= body.max_claims <= TRANSFER_MAX_CLAIMS):
        raise HTTPException(400, f"Количество получателей: 1–{TRANSFER_MAX_CLAIMS}")

    amount_per_claim = body.total_rub // body.max_claims
    if amount_per_claim < 1:
        raise HTTPException(400, "Слишком малая сумма")
    # Only what can actually be claimed leaves the sender; the remainder stays put.
    total = amount_per_claim * body.max_claims

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)

        transfer = Transfer(
            code=secrets.token_urlsafe(12),
            sender_id=player.id,
            amount_per_claim=amount_per_claim,
            max_claims=body.max_claims,
            expires_at=utcnow() + timedelta(hours=TRANSFER_TTL_HOURS),
        )
        session.add(transfer)
        session.flush()
        ledger.spend(session, player, "rub", total, "transfer_send", ref_table="transfers", ref_id=transfer.id)

        result = {"code": transfer.code, "total_rub": total, "new_rub": ledger.balance(player, "rub")}
        session.commit()
        return result


def transfer_claim(tg_id: int, code: str) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")

        transfer = session.scalars(
            select(Transfer).where(Transfer.code == code).with_for_update()
        ).first()
        if not transfer:
            raise HTTPException(404, "Ссылка не найдена")
        if transfer.closed_at is not None or transfer.claims_used >= transfer.max_claims:
            raise HTTPException(400, "Ссылка уже израсходована")
        if transfer.expires_at <= utcnow():
            raise HTTPException(400, "Срок действия ссылки истёк")
        if transfer.sender_id == player.id:
            raise HTTPException(400, "Нельзя получить собственный перевод")

        amount = int(transfer.amount_per_claim)
        session.add(
            TransferClaim(transfer_id=transfer.id, player_id=player.id, amount_rub=amount)
        )
        transfer.claims_used += 1
        if transfer.claims_used >= transfer.max_claims:
            transfer.closed_at = utcnow()
        ledger.grant(session, player, "rub", amount, "transfer_claim", ref_table="transfers", ref_id=transfer.id)

        new_rub = ledger.balance(player, "rub")
        try:
            session.commit()
        except IntegrityError as exc:
            # The composite primary key on (transfer_id, player_id) blocks a second claim.
            session.rollback()
            raise HTTPException(400, "Ты уже получил этот перевод") from exc

        return {"ok": True, "rub_received": amount, "new_rub": new_rub}


def my_transfers(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            return {"transfers": []}
        rows = session.scalars(
            select(Transfer)
            .where(Transfer.sender_id == player.id)
            .order_by(Transfer.created_at.desc())
            .limit(20)
        ).all()
        return {
            "transfers": [
                {
                    "code": row.code,
                    "total_rub": row.amount_per_claim * row.max_claims,
                    "rub_per_claim": row.amount_per_claim,
                    "max_claims": row.max_claims,
                    "claims": row.claims_used,
                    "active": row.closed_at is None and row.expires_at > utcnow(),
                    "created_at": row.created_at.isoformat(),
                    "expires_at": row.expires_at.isoformat(),
                }
                for row in rows
            ]
        }
