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
from api.app.db.models import (
    Animal,
    Clan,
    ClanJoinRequest,
    ClanMember,
    Item,
    Locality,
    Player,
    Transfer,
    TransferClaim,
    utcnow,
)
from api.app.schemas.social import (
    ClanCreateBody,
    ClanJoinDecisionBody,
    ClanMemberActionBody,
    ClanRequestBody,
    ClanSpecializationBody,
    TransferCreateBody,
)
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
from api.app.zoopark.income import count_alive_animals, on_expedition_subquery, sync_player_income
from api.app.zoopark.profile import get_clan, get_player, item_payload
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
                Animal.id.not_in(on_expedition_subquery()),
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
        active_items = session.scalars(
            select(Item).where(Item.player_id == target.id, Item.is_active.is_(True)).order_by(Item.created_at.asc(), Item.id.asc())
        ).all()

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
            "active_items": [item_payload(item) for item in active_items],
        }


# ─── Clans ────────────────────────────────────────────────────────────────────

CLAN_SPECIALIZATIONS = {
    "specialist": {
        "name": "🔬 Редкий зверинец",
        "description": "+50% дохода от эпических, мифических и легендарных животных; −20% от редких.",
    },
    "megapark": {
        "name": "🏟 Мегапарк",
        "description": "+1% дохода за каждые 10 животных (до +60%); +15% к содержанию.",
    },
    "wild": {
        "name": "🌿 Дикий заповедник",
        "description": "+3% дохода за каждый уникальный вид.",
    },
}

def _member_counts(session: Session) -> dict[int, int]:
    rows = session.execute(
        select(ClanMember.clan_id, func.count(ClanMember.player_id)).group_by(ClanMember.clan_id)
    ).all()
    return {clan_id: int(count) for clan_id, count in rows}


def _clan_entry(
    clan: Clan,
    count: int,
    owner_nickname: str,
    *,
    join_request_status: str | None = None,
    include_invite: bool = False,
) -> dict:
    specialization = CLAN_SPECIALIZATIONS.get(clan.specialization or "")
    return {
        "id": clan.id,
        "name": clan.name,
        "level": clan.level,
        "member_count": count,
        "owner_nickname": owner_nickname,
        "specialization": clan.specialization,
        "specialization_name": specialization["name"] if specialization else None,
        "join_request_status": join_request_status,
        "invite_code": clan.invite_code if include_invite else None,
    }


def _my_membership(session: Session, player_id: int) -> ClanMember | None:
    return session.scalars(select(ClanMember).where(ClanMember.player_id == player_id)).first()


def _clan_owner(session: Session, player: Player) -> tuple[Clan, ClanMember]:
    membership = _my_membership(session, player.id)
    if membership is None:
        raise HTTPException(400, "Ты не в клане")
    clan = session.get(Clan, membership.clan_id, with_for_update=True)
    if clan is None or clan.owner_id != player.id or membership.role != "owner":
        raise HTTPException(403, "Только владелец клана может выполнить это действие")
    return clan, membership


def clan_list(tg_id: int) -> dict:
    with get_session() as session:
        me = get_player(session, tg_id)
        my_membership = _my_membership(session, me.id) if me else None
        clans = session.scalars(select(Clan).order_by(Clan.level.desc(), Clan.id.asc()).limit(20)).all()
        counts = _member_counts(session)
        owners = {
            player.id: player.nickname
            for player in session.scalars(
                select(Player).where(Player.id.in_([clan.owner_id for clan in clans] or [0]))
            ).all()
        }
        # Signed out, there is no request to look up — the branch used to ask the database
        # for `WHERE false`, which is a query round trip to learn what the `if` already knew.
        request_statuses: dict[int, str] = {}
        if me:
            request_statuses = {
                request.clan_id: request.status
                for request in session.scalars(
                    select(ClanJoinRequest).where(ClanJoinRequest.player_id == me.id)
                ).all()
            }

        payload = []
        my_clan = None
        for clan in clans:
            entry = _clan_entry(
                clan,
                counts.get(clan.id, 0),
                owners.get(clan.owner_id, "—"),
                join_request_status=request_statuses.get(clan.id),
            )
            payload.append(entry)
            if my_membership and my_membership.clan_id == clan.id:
                my_clan = _clan_entry(
                    clan,
                    counts.get(clan.id, 0),
                    owners.get(clan.owner_id, "—"),
                    join_request_status=None,
                    include_invite=True,
                )

        return {
            "clans": payload,
            "my_clan": my_clan,
            "my_role": my_membership.role if my_membership else None,
        }


def clan_details(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        membership = _my_membership(session, player.id)
        if membership is None:
            raise HTTPException(400, "Ты не в клане")
        clan = session.get(Clan, membership.clan_id)
        assert clan is not None
        members = session.scalars(select(ClanMember).where(ClanMember.clan_id == clan.id)).all()
        total_income = sum(int(member.player.income_rub_per_min) for member in members)
        animal_counts = {member.player_id: count_alive_animals(session, member.player_id) for member in members}
        requirements = _level_requirements(clan.level, len(members), total_income, animal_counts)
        owner = session.get(Player, clan.owner_id)
        return {
            "clan": _clan_entry(clan, len(members), owner.nickname if owner else "—"),
            "my_role": membership.role,
            "specializations": CLAN_SPECIALIZATIONS,
            "level": clan.level,
            "next_level": clan.level + 1 if clan.level < 3 else None,
            "requirements": requirements,
            "can_upgrade": all(item["met"] for item in requirements),
            "invite_code": clan.invite_code,
            "join_requests": [
                {
                    "id": request.id,
                    "player_tg_id": request.player.telegram_id,
                    "player_nickname": request.player.nickname,
                    "created_at": request.created_at.isoformat(),
                }
                for request in session.scalars(
                    select(ClanJoinRequest)
                    .where(ClanJoinRequest.clan_id == clan.id, ClanJoinRequest.status == "pending")
                    .order_by(ClanJoinRequest.created_at.asc(), ClanJoinRequest.id.asc())
                ).all()
            ] if membership.role == "owner" else [],
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

        clan = Clan(name=name, invite_code=secrets.token_urlsafe(12), owner_id=player.id)
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

        if _my_membership(session, player.id):
            raise HTTPException(400, "Ты уже в клане")
        members = session.scalar(select(func.count(ClanMember.player_id)).where(ClanMember.clan_id == clan.id)) or 0
        if members >= CLAN_MAX_MEMBERS:
            raise HTTPException(400, f"В клане уже {CLAN_MAX_MEMBERS} участников")

        request = session.scalars(
            select(ClanJoinRequest)
            .where(ClanJoinRequest.clan_id == clan.id, ClanJoinRequest.player_id == player.id)
            .with_for_update()
        ).first()
        if request and request.status == "pending":
            return {
                "ok": True,
                "status": "pending",
                "message": "Заявка уже отправлена. Глава клана рассмотрит её и примет или отклонит.",
            }
        if request:
            request.status = "pending"
            request.created_at = utcnow()
            request.decided_at = None
        else:
            request = ClanJoinRequest(clan_id=clan.id, player_id=player.id, status="pending")
            session.add(request)
        try:
            session.flush()
        except IntegrityError as exc:
            raise HTTPException(400, "Ты уже в клане") from exc

        result = {
            "ok": True,
            "status": "pending",
            "message": "Заявка отправлена. Глава клана рассмотрит её и примет или отклонит.",
        }
        session.commit()
        return result


def clan_decide_join_request(tg_id: int, body: ClanJoinDecisionBody) -> dict:
    with get_session() as session:
        owner = get_player(session, tg_id, for_update=True)
        if not owner:
            raise HTTPException(404, "Нет игрока")
        clan, _ = _clan_owner(session, owner)
        request = session.get(ClanJoinRequest, body.request_id, with_for_update=True)
        if request is None or request.clan_id != clan.id:
            raise HTTPException(404, "Заявка не найдена")
        if request.status != "pending":
            raise HTTPException(400, "Эта заявка уже рассмотрена")

        request.decided_at = utcnow()
        if body.decision == "reject":
            request.status = "rejected"
            session.commit()
            return {"ok": True, "decision": "reject", "message": f"Заявка игрока {request.player.nickname} отклонена"}

        target = session.get(Player, request.player_id, with_for_update=True)
        if target is None:
            request.status = "rejected"
            session.commit()
            raise HTTPException(404, "Игрок не найден")
        if _my_membership(session, target.id):
            request.status = "rejected"
            session.commit()
            raise HTTPException(400, "Игрок уже состоит в клане")
        members = session.scalar(select(func.count(ClanMember.player_id)).where(ClanMember.clan_id == clan.id)) or 0
        if members >= CLAN_MAX_MEMBERS:
            raise HTTPException(400, f"В клане уже {CLAN_MAX_MEMBERS} участников")

        request.status = "accepted"
        session.add(ClanMember(clan_id=clan.id, player_id=target.id, role="member"))
        sync_player_income(session, target)
        session.commit()
        return {"ok": True, "decision": "accept", "message": f"{target.nickname} принят в клан"}


def clan_remove_member(tg_id: int, body: ClanMemberActionBody) -> dict:
    with get_session() as session:
        owner = get_player(session, tg_id, for_update=True)
        if not owner:
            raise HTTPException(404, "Нет игрока")
        clan, _ = _clan_owner(session, owner)
        target = session.scalars(
            select(Player).where(Player.telegram_id == body.target_tg_id).with_for_update()
        ).first()
        if not target:
            raise HTTPException(404, "Участник не найден")
        if target.id == owner.id:
            raise HTTPException(400, "Владелец не может удалить себя")
        membership = session.scalars(
            select(ClanMember).where(
                ClanMember.clan_id == clan.id,
                ClanMember.player_id == target.id,
            ).with_for_update()
        ).first()
        if membership is None:
            raise HTTPException(404, "Игрок не состоит в этом клане")

        session.delete(membership)
        # A clan specialization affects income, so removing a member must invalidate the
        # cached income immediately rather than waiting for their next request.
        sync_player_income(session, target)
        session.commit()
        return {"ok": True, "target_tg_id": target.telegram_id, "message": f"{target.nickname} удалён из клана"}


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
                "id": member.id,
                "tg_id": member.telegram_id,
                "nickname": member.nickname,
                "role": role,
                "income_rub_per_min": member.income_rub_per_min,
                "animals_count": count_alive_animals(session, member.id),
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
        if clan is not None and clan.owner_id == player.id:
            next_member = session.scalars(
                select(ClanMember).where(ClanMember.clan_id == clan.id).order_by(ClanMember.joined_at.asc(), ClanMember.player_id.asc())
            ).first()
            if next_member is None:
                session.delete(clan)
            else:
                next_member.role = "owner"
                clan.owner_id = next_member.player_id

        session.commit()
        return {"ok": True, "message": "Покинул клан"}


def _level_requirements(level: int, member_count: int, total_income: int, animal_counts: dict[int, int]) -> list[dict]:
    if level >= 3:
        return []
    if level == 1:
        return [{"key": "members", "label": "Участников", "current": member_count, "target": 3, "met": member_count >= 3}]
    return [
        {"key": "members", "label": "Участников", "current": member_count, "target": 5, "met": member_count >= 5},
        {"key": "income", "label": "Доход клана ₽/мин", "current": total_income, "target": 1000, "met": total_income >= 1000},
        {"key": "animals", "label": "Животных у каждого", "current": min(animal_counts.values(), default=0), "target": 5, "met": min(animal_counts.values(), default=0) >= 5},
    ]


def clan_level_up(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        clan, _ = _clan_owner(session, player)
        members = session.scalars(select(ClanMember).where(ClanMember.clan_id == clan.id)).all()
        counts = {member.player_id: count_alive_animals(session, member.player_id) for member in members}
        requirements = _level_requirements(clan.level, len(members), sum(int(member.player.income_rub_per_min) for member in members), counts)
        if clan.level >= 3:
            raise HTTPException(400, "Клан уже достиг максимального уровня")
        if not all(item["met"] for item in requirements):
            raise HTTPException(400, "Условия повышения уровня ещё не выполнены")
        clan.level += 1
        session.commit()
        return {"ok": True, "level": clan.level, "message": f"Клан достиг {clan.level}-го уровня"}


def clan_choose_specialization(tg_id: int, body: ClanSpecializationBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        clan, _ = _clan_owner(session, player)
        if clan.level < 3:
            raise HTTPException(400, "Специализация открывается на 3-м уровне")
        if clan.specialization:
            raise HTTPException(400, "Специализация уже выбрана")
        clan.specialization = body.specialization
        for member in session.scalars(select(ClanMember).where(ClanMember.clan_id == clan.id)).all():
            member_player = session.get(Player, member.player_id, with_for_update=True)
            if member_player:
                sync_player_income(session, member_player)
        session.commit()
        spec = CLAN_SPECIALIZATIONS[body.specialization]
        return {"ok": True, "specialization": body.specialization, "message": f"Выбрано: {spec['name']}"}


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
            currency=body.currency,
            amount_per_claim=amount_per_claim,
            max_claims=body.max_claims,
            expires_at=utcnow() + timedelta(hours=TRANSFER_TTL_HOURS),
        )
        session.add(transfer)
        session.flush()
        ledger.spend(session, player, body.currency, total, "transfer_send", ref_table="transfers", ref_id=transfer.id)

        result = {
            "code": transfer.code,
            "currency": body.currency,
            "total_amount": total,
            "amount_per_claim": amount_per_claim,
            f"new_{body.currency}": ledger.balance(player, body.currency),
        }
        # Keep the old response fields for clients that still understand ruble-only transfers.
        if body.currency == "rub":
            result.update({"total_rub": total, "new_rub": ledger.balance(player, "rub")})
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
        currency = ledger.as_currency(transfer.currency)
        ledger.grant(session, player, currency, amount, "transfer_claim", ref_table="transfers", ref_id=transfer.id)

        new_balance = ledger.balance(player, currency)
        try:
            session.commit()
        except IntegrityError as exc:
            # The composite primary key on (transfer_id, player_id) blocks a second claim.
            session.rollback()
            raise HTTPException(400, "Ты уже получил этот перевод") from exc

        result = {
            "ok": True,
            "currency": transfer.currency,
            "amount_received": amount,
            f"new_{transfer.currency}": new_balance,
        }
        if transfer.currency == "rub":
            result["rub_received"] = amount
            result["new_rub"] = new_balance
        return result


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
                    "currency": row.currency,
                    "total_amount": row.amount_per_claim * row.max_claims,
                    "amount_per_claim": row.amount_per_claim,
                    "total_rub": row.amount_per_claim * row.max_claims if row.currency == "rub" else None,
                    "rub_per_claim": row.amount_per_claim if row.currency == "rub" else None,
                    "max_claims": row.max_claims,
                    "claims": row.claims_used,
                    "active": row.closed_at is None and row.expires_at > utcnow(),
                    "created_at": row.created_at.isoformat(),
                    "expires_at": row.expires_at.isoformat(),
                }
                for row in rows
            ]
        }
