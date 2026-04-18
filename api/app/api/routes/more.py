"""Endpoints for the 'More' section: achievements, daily bonus, top, clans, referrals, transfers, merchant."""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.app.core.auth import require_telegram_id
from api.app.core.errors import AppError
from api.app.db.session import get_db_session
from api.app.services import achievement_service, profile_service
from api.app.services.logic import utc_now
from api.app.services.serializers import build_profile_response

router = APIRouter(prefix="/api", tags=["more"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _today_start() -> datetime:
    now = _utc_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _get_player(db: Session, telegram_id: int):
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    db.commit()
    return profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)


# ─── Achievements ─────────────────────────────────────────────────────────────

class AchievementOut(BaseModel):
    id: str
    name: str
    description: str
    order: int
    cosmetic_id: str
    progress: float
    unlocked: bool
    unlocked_at: datetime | None


class AchievementsResponse(BaseModel):
    achievements: list[AchievementOut]
    active_cosmetic_id: str | None
    newly_unlocked: list[str]


class EquipCosmeticRequest(BaseModel):
    cosmetic_id: str | None


class EquipCosmeticResponse(BaseModel):
    active_cosmetic_id: str | None


@router.get("/achievements", response_model=AchievementsResponse)
def get_achievements(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> AchievementsResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)
    states, newly_unlocked = achievement_service.sync_achievements(db, profile, now)
    db.commit()
    active_cosmetic = achievement_service.get_active_cosmetic_id(profile)

    return AchievementsResponse(
        achievements=[
            AchievementOut(
                id=s.definition.id,
                name=s.definition.name,
                description=s.definition.description,
                order=s.definition.order,
                cosmetic_id=s.definition.cosmetic_id,
                progress=s.progress,
                unlocked=s.unlocked,
                unlocked_at=s.unlocked_at,
            )
            for s in states
        ],
        active_cosmetic_id=active_cosmetic,
        newly_unlocked=newly_unlocked,
    )


@router.post("/achievements/equip", response_model=EquipCosmeticResponse)
def equip_achievement_cosmetic(
    body: EquipCosmeticRequest,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> EquipCosmeticResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    cosmetic_id = achievement_service.equip_cosmetic(db, profile, body.cosmetic_id)
    db.commit()
    return EquipCosmeticResponse(active_cosmetic_id=cosmetic_id)


# ─── Leaderboard ──────────────────────────────────────────────────────────────

class LeaderEntry(BaseModel):
    rank: int
    player_id: int
    nickname: str
    income_per_hour: str
    animal_count: int
    is_me: bool


class LeaderboardResponse(BaseModel):
    entries: list[LeaderEntry]
    my_rank: int | None


@router.get("/top", response_model=LeaderboardResponse)
def get_top(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> LeaderboardResponse:
    # income = 24 * survival_mult * appearance_mult * size_mult * terrain_mult (if habitat set and matches)
    rows = db.execute(text("""
        SELECT
            p.id,
            p.telegram_id,
            p.nickname,
            COALESCE(SUM(
                CASE WHEN a.status = 'active' AND a.current_habitat_id IS NOT NULL THEN
                    24.0
                    * CASE a.survival_gene WHEN 'low' THEN 0.7 WHEN 'medium' THEN 1.0 ELSE 1.3 END
                    * CASE a.appearance_gene WHEN 'low' THEN 0.6 WHEN 'medium' THEN 1.0 ELSE 1.5 END
                    * CASE a.size_gene WHEN 'low' THEN 0.8 WHEN 'medium' THEN 1.0 ELSE 1.4 END
                    * CASE WHEN h.terrain_type = a.habitat_preference THEN 1.5 ELSE 1.0 END
                ELSE 0 END
            ), 0) AS income,
            COUNT(CASE WHEN a.status != 'dead' THEN 1 END) AS animal_count
        FROM players p
        LEFT JOIN player_seasons ps ON ps.player_id = p.id
        LEFT JOIN animals a ON a.player_season_id = ps.id
        LEFT JOIN player_habitats h ON h.id = a.current_habitat_id
        GROUP BY p.id, p.telegram_id, p.nickname
        ORDER BY income DESC
        LIMIT 50
    """)).fetchall()

    my_player_id: int | None = None
    try:
        my_player_id = db.execute(
            text("SELECT id FROM players WHERE telegram_id = :tid"),
            {"tid": telegram_id}
        ).scalar()
    except Exception:
        pass

    entries = []
    my_rank = None
    for i, row in enumerate(rows):
        rank = i + 1
        is_me = row[0] == my_player_id
        if is_me:
            my_rank = rank
        entries.append(LeaderEntry(
            rank=rank,
            player_id=row[0],
            nickname=row[2],
            income_per_hour=str(row[3]),
            animal_count=int(row[4]),
            is_me=is_me,
        ))

    return LeaderboardResponse(entries=entries, my_rank=my_rank)


# ─── Daily Bonus ──────────────────────────────────────────────────────────────

DAILY_BONUS_BASE = Decimal("100")
STREAK_MULTIPLIER = Decimal("0.1")  # +10% per streak day

class DailyBonusStatus(BaseModel):
    available: bool
    next_claim_at: datetime | None
    current_streak: int
    coins_if_claimed: str


class DailyBonusClaim(BaseModel):
    coins_awarded: str
    new_streak: int
    balance_coins: str


@router.get("/daily-bonus/status", response_model=DailyBonusStatus)
def daily_bonus_status(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> DailyBonusStatus:
    player_id = db.execute(
        text("SELECT id FROM players WHERE telegram_id = :tid"), {"tid": telegram_id}
    ).scalar()
    if not player_id:
        raise AppError("Player not found", 404)

    today = _today_start()
    last = db.execute(
        text("SELECT claimed_at, day_streak FROM daily_claims WHERE player_id = :pid ORDER BY claimed_at DESC LIMIT 1"),
        {"pid": player_id},
    ).fetchone()

    if last:
        last_dt = last[0] if isinstance(last[0], datetime) else datetime.fromisoformat(str(last[0]))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        last_day = last_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        available = last_day < today
        streak = last[1] if available else last[1]
        next_claim = (today + timedelta(days=1)) if not available else None
    else:
        available = True
        streak = 0
        next_claim = None

    preview_streak = streak + 1 if available else streak
    bonus = DAILY_BONUS_BASE * (1 + STREAK_MULTIPLIER * (preview_streak - 1))

    return DailyBonusStatus(
        available=available,
        next_claim_at=next_claim,
        current_streak=streak,
        coins_if_claimed=str(round(bonus, 2)),
    )


@router.post("/daily-bonus/claim", response_model=DailyBonusClaim)
def claim_daily_bonus(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> DailyBonusClaim:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    player_id = profile.player.id

    today = _today_start()
    last = db.execute(
        text("SELECT claimed_at, day_streak FROM daily_claims WHERE player_id = :pid ORDER BY claimed_at DESC LIMIT 1"),
        {"pid": player_id},
    ).fetchone()

    if last:
        last_dt = last[0] if isinstance(last[0], datetime) else datetime.fromisoformat(str(last[0]))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        last_day = last_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if last_day >= today:
            raise AppError("Бонус уже получен сегодня", 409)
        yesterday = today - timedelta(days=1)
        new_streak = last[1] + 1 if last_day >= yesterday else 1
    else:
        new_streak = 1

    bonus = DAILY_BONUS_BASE * (1 + STREAK_MULTIPLIER * (new_streak - 1))

    db.execute(text(
        "INSERT INTO daily_claims (player_id, coins_awarded, day_streak) VALUES (:pid, :coins, :streak)"
    ), {"pid": player_id, "coins": float(bonus), "streak": new_streak})

    # Credit coins to player_season balance
    ps = profile.player_seasons[-1] if profile.player_seasons else None
    if ps:
        ps.balance_coins = (ps.balance_coins or Decimal("0")) + bonus

    db.commit()

    new_balance = str(ps.balance_coins) if ps else "0"
    return DailyBonusClaim(
        coins_awarded=str(round(bonus, 2)),
        new_streak=new_streak,
        balance_coins=new_balance,
    )


# ─── Random Merchant ──────────────────────────────────────────────────────────

class MerchantOffer(BaseModel):
    animal_id: str
    terrain_type: str
    income_per_hour: str
    combat_power: int
    survival_gene: str
    breeding_gene: str
    appearance_gene: str
    size_gene: str
    original_price: str
    discount_pct: int
    final_price: str


class MerchantResponse(BaseModel):
    offers: list[MerchantOffer]
    refreshes_at: datetime


@router.get("/merchant", response_model=MerchantResponse)
def get_merchant(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> MerchantResponse:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    profile_service.sync_profile_state(db, profile, now)

    # Предлагаем животных с хорошими генами из зоопарка игрока
    live = [a for a in profile.animals if a.status == "active"]
    if not live:
        raise AppError("У тебя нет живых животных для торговца", 404)

    import random
    selected = random.sample(live, min(3, len(live)))
    discounts = [30, 40, 50]

    offers = []
    for i, animal in enumerate(selected):
        discount = discounts[i % len(discounts)]
        base_price = Decimal("120") + Decimal(str(animal.combat_power)) * Decimal("10")
        final = base_price * (1 - Decimal(str(discount)) / 100)
        offers.append(MerchantOffer(
            animal_id=animal.id,
            terrain_type=animal.habitat_preference,
            income_per_hour=str(animal.income_per_hour),
            combat_power=animal.combat_power,
            survival_gene=animal.survival_gene,
            breeding_gene=animal.breeding_gene,
            appearance_gene=animal.appearance_gene,
            size_gene=animal.size_gene,
            original_price=str(round(base_price, 2)),
            discount_pct=discount,
            final_price=str(round(final, 2)),
        ))

    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    return MerchantResponse(offers=offers, refreshes_at=tomorrow)


# ─── Clan ─────────────────────────────────────────────────────────────────────

class ClanOut(BaseModel):
    id: int
    name: str
    tag: str
    description: str | None
    level: int
    member_count: int
    owner_nickname: str


class ClanListResponse(BaseModel):
    clans: list[ClanOut]
    my_clan: ClanOut | None


class CreateClanRequest(BaseModel):
    name: str = Field(min_length=3, max_length=64)
    tag: str = Field(min_length=2, max_length=8)
    description: str | None = Field(default=None, max_length=256)


class ClanResponse(BaseModel):
    clan: ClanOut
    message: str


def _build_clan_out(row: Any) -> ClanOut:
    return ClanOut(
        id=row[0], name=row[1], tag=row[2],
        description=row[3], level=row[4],
        member_count=row[5], owner_nickname=row[6],
    )


@router.get("/clan/list", response_model=ClanListResponse)
def clan_list(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> ClanListResponse:
    my_player_id = db.execute(
        text("SELECT id FROM players WHERE telegram_id = :tid"), {"tid": telegram_id}
    ).scalar()

    rows = db.execute(text("""
        SELECT c.id, c.name, c.tag, c.description, c.level,
               COUNT(cm.id) AS member_count,
               p.nickname AS owner_nickname
        FROM clans c
        JOIN players p ON p.id = c.owner_id
        LEFT JOIN clan_members cm ON cm.clan_id = c.id
        GROUP BY c.id, c.name, c.tag, c.description, c.level, p.nickname
        ORDER BY c.level DESC, member_count DESC
        LIMIT 20
    """)).fetchall()

    my_clan_row = None
    if my_player_id:
        my_clan_row = db.execute(text("""
            SELECT c.id, c.name, c.tag, c.description, c.level,
                   COUNT(cm2.id) AS member_count,
                   p.nickname AS owner_nickname
            FROM clan_members cm
            JOIN clans c ON c.id = cm.clan_id
            JOIN players p ON p.id = c.owner_id
            LEFT JOIN clan_members cm2 ON cm2.clan_id = c.id
            WHERE cm.player_id = :pid
            GROUP BY c.id, c.name, c.tag, c.description, c.level, p.nickname
            LIMIT 1
        """), {"pid": my_player_id}).fetchone()

    return ClanListResponse(
        clans=[_build_clan_out(r) for r in rows],
        my_clan=_build_clan_out(my_clan_row) if my_clan_row else None,
    )


@router.post("/clan/create", response_model=ClanResponse)
def create_clan(
    body: CreateClanRequest,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> ClanResponse:
    my_player_id = db.execute(
        text("SELECT id FROM players WHERE telegram_id = :tid"), {"tid": telegram_id}
    ).scalar()
    if not my_player_id:
        raise AppError("Игрок не найден", 404)

    already = db.execute(
        text("SELECT id FROM clan_members WHERE player_id = :pid"), {"pid": my_player_id}
    ).scalar()
    if already:
        raise AppError("Ты уже состоишь в клане", 409)

    exists_name = db.execute(text("SELECT id FROM clans WHERE name = :n"), {"n": body.name}).scalar()
    if exists_name:
        raise AppError("Клан с таким именем уже существует", 409)

    exists_tag = db.execute(text("SELECT id FROM clans WHERE tag = :t"), {"t": body.tag}).scalar()
    if exists_tag:
        raise AppError("Клан с таким тегом уже существует", 409)

    db.execute(text(
        "INSERT INTO clans (name, tag, description, owner_id, level) VALUES (:name, :tag, :desc, :owner, 1)"
    ), {"name": body.name, "tag": body.tag, "desc": body.description, "owner": my_player_id})
    clan_id = db.execute(text("SELECT last_insert_rowid()")).scalar() or \
              db.execute(text("SELECT id FROM clans WHERE name = :n"), {"n": body.name}).scalar()

    db.execute(text(
        "INSERT INTO clan_members (clan_id, player_id, role) VALUES (:cid, :pid, 'owner')"
    ), {"cid": clan_id, "pid": my_player_id})
    db.commit()

    row = db.execute(text("""
        SELECT c.id, c.name, c.tag, c.description, c.level, 1, p.nickname
        FROM clans c JOIN players p ON p.id = c.owner_id WHERE c.id = :cid
    """), {"cid": clan_id}).fetchone()

    return ClanResponse(clan=_build_clan_out(row), message="Клан создан!")


@router.post("/clan/join/{clan_id}", response_model=ClanResponse)
def join_clan(
    clan_id: int,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> ClanResponse:
    my_player_id = db.execute(
        text("SELECT id FROM players WHERE telegram_id = :tid"), {"tid": telegram_id}
    ).scalar()
    if not my_player_id:
        raise AppError("Игрок не найден", 404)

    already = db.execute(
        text("SELECT id FROM clan_members WHERE player_id = :pid"), {"pid": my_player_id}
    ).scalar()
    if already:
        raise AppError("Ты уже в клане", 409)

    clan = db.execute(text("SELECT id FROM clans WHERE id = :cid"), {"cid": clan_id}).scalar()
    if not clan:
        raise AppError("Клан не найден", 404)

    db.execute(text(
        "INSERT INTO clan_members (clan_id, player_id, role) VALUES (:cid, :pid, 'member')"
    ), {"cid": clan_id, "pid": my_player_id})
    db.commit()

    row = db.execute(text("""
        SELECT c.id, c.name, c.tag, c.description, c.level,
               COUNT(cm.id), p.nickname
        FROM clans c JOIN players p ON p.id = c.owner_id
        LEFT JOIN clan_members cm ON cm.clan_id = c.id
        WHERE c.id = :cid GROUP BY c.id
    """), {"cid": clan_id}).fetchone()

    return ClanResponse(clan=_build_clan_out(row), message="Ты вступил в клан!")


@router.post("/clan/leave", response_model=dict)
def leave_clan(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> dict:
    my_player_id = db.execute(
        text("SELECT id FROM players WHERE telegram_id = :tid"), {"tid": telegram_id}
    ).scalar()

    member = db.execute(
        text("SELECT id, clan_id, role FROM clan_members WHERE player_id = :pid"), {"pid": my_player_id}
    ).fetchone()
    if not member:
        raise AppError("Ты не в клане", 404)
    if member[2] == "owner":
        raise AppError("Владелец не может покинуть клан. Сначала передай лидерство или удали клан.", 409)

    db.execute(text("DELETE FROM clan_members WHERE id = :id"), {"id": member[0]})
    db.commit()
    return {"ok": True, "message": "Ты покинул клан"}


# ─── Referrals ────────────────────────────────────────────────────────────────

class ReferralInfo(BaseModel):
    referral_code: str
    total_referrals: int
    reward_per_referral: str
    referred_players: list[str]


@router.get("/referrals", response_model=ReferralInfo)
def get_referrals(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> ReferralInfo:
    my_player_id = db.execute(
        text("SELECT id FROM players WHERE telegram_id = :tid"), {"tid": telegram_id}
    ).scalar()
    if not my_player_id:
        raise AppError("Игрок не найден", 404)

    refs = db.execute(text("""
        SELECT p.nickname FROM referrals r
        JOIN players p ON p.id = r.referred_id
        WHERE r.referrer_id = :pid
        ORDER BY r.referred_at DESC
        LIMIT 20
    """), {"pid": my_player_id}).fetchall()

    code = f"mm_{telegram_id}"
    return ReferralInfo(
        referral_code=code,
        total_referrals=len(refs),
        reward_per_referral="200",
        referred_players=[r[0] for r in refs],
    )


# ─── Transfers (Money Giveaway) ───────────────────────────────────────────────

class CreateTransferRequest(BaseModel):
    total_coins: Decimal = Field(gt=0)
    max_claims: int = Field(ge=1, le=100)


class TransferOut(BaseModel):
    key: str
    total_coins: str
    coins_per_claim: str
    max_claims: int
    claims_count: int
    is_active: bool
    created_at: datetime


class TransferListResponse(BaseModel):
    transfers: list[TransferOut]


def _gen_key() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


@router.post("/transfers/create", response_model=TransferOut)
def create_transfer(
    body: CreateTransferRequest,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> TransferOut:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    ps = profile.player_seasons[-1] if profile.player_seasons else None
    if not ps or ps.balance_coins < body.total_coins:
        raise AppError("Недостаточно монет", 409)

    key = _gen_key()
    coins_per_claim = round(body.total_coins / body.max_claims, 2)
    ps.balance_coins -= body.total_coins

    db.execute(text("""
        INSERT INTO money_transfers (creator_id, key, total_coins, coins_per_claim, max_claims, claims_count, is_active)
        VALUES (:cid, :key, :total, :per_claim, :max_c, 0, 1)
    """), {
        "cid": profile.player.id, "key": key,
        "total": float(body.total_coins), "per_claim": float(coins_per_claim),
        "max_c": body.max_claims,
    })
    db.commit()

    return TransferOut(
        key=key,
        total_coins=str(body.total_coins),
        coins_per_claim=str(coins_per_claim),
        max_claims=body.max_claims,
        claims_count=0,
        is_active=True,
        created_at=now,
    )


@router.get("/transfers/my", response_model=TransferListResponse)
def my_transfers(
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> TransferListResponse:
    my_player_id = db.execute(
        text("SELECT id FROM players WHERE telegram_id = :tid"), {"tid": telegram_id}
    ).scalar()

    rows = db.execute(text("""
        SELECT key, total_coins, coins_per_claim, max_claims, claims_count, is_active, created_at
        FROM money_transfers WHERE creator_id = :pid ORDER BY created_at DESC LIMIT 10
    """), {"pid": my_player_id}).fetchall()

    return TransferListResponse(transfers=[
        TransferOut(key=r[0], total_coins=str(r[1]), coins_per_claim=str(r[2]),
                    max_claims=r[3], claims_count=r[4], is_active=bool(r[5]),
                    created_at=r[6] if isinstance(r[6], datetime) else datetime.fromisoformat(str(r[6])))
        for r in rows
    ])


@router.post("/transfers/{key}/claim", response_model=dict)
def claim_transfer(
    key: str,
    telegram_id: int = Depends(require_telegram_id),
    db: Session = Depends(get_db_session),
) -> dict:
    now = utc_now()
    profile = profile_service.get_current_profile_by_telegram_id(db, telegram_id, now)
    player_id = profile.player.id

    transfer = db.execute(text(
        "SELECT id, coins_per_claim, max_claims, claims_count, is_active, creator_id FROM money_transfers WHERE key = :k"
    ), {"k": key}).fetchone()
    if not transfer:
        raise AppError("Ссылка не найдена", 404)
    if not transfer[4]:
        raise AppError("Раздача закончилась", 409)
    if transfer[5] == player_id:
        raise AppError("Нельзя забрать из своей раздачи", 409)
    if transfer[3] >= transfer[2]:
        raise AppError("Все слоты уже заняты", 409)

    already = db.execute(text(
        "SELECT id FROM transfer_claims WHERE transfer_id = :tid AND player_id = :pid"
    ), {"tid": transfer[0], "pid": player_id}).scalar()
    if already:
        raise AppError("Ты уже получил из этой раздачи", 409)

    coins = Decimal(str(transfer[1]))
    ps = profile.player_seasons[-1] if profile.player_seasons else None
    if ps:
        ps.balance_coins = (ps.balance_coins or Decimal("0")) + coins

    db.execute(text(
        "INSERT INTO transfer_claims (transfer_id, player_id) VALUES (:tid, :pid)"
    ), {"tid": transfer[0], "pid": player_id})
    new_count = transfer[3] + 1
    is_active = 1 if new_count < transfer[2] else 0
    db.execute(text(
        "UPDATE money_transfers SET claims_count = :c, is_active = :a WHERE id = :id"
    ), {"c": new_count, "a": is_active, "id": transfer[0]})
    db.commit()

    return {"ok": True, "coins_received": str(coins), "new_balance": str(ps.balance_coins if ps else 0)}
