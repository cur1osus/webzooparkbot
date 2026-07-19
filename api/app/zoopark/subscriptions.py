"""Subscription rewards for the official ZooPark communities."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.core.config import (
    SOCIAL_REWARD_AMOUNT,
    SOCIAL_REWARD_CHANNEL_ID,
    SOCIAL_REWARD_CHANNEL_URL,
    SOCIAL_REWARD_CHAT_ID,
    SOCIAL_REWARD_CHAT_URL,
)
from api.app.core.telegram import TelegramApiError, call_bot_api
from api.app.db.connection import get_session
from api.app.db.models import Player, SocialMembership, utcnow
from api.app.zoopark import ledger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RewardTarget:
    key: str
    chat_id: int
    title: str
    url: str


TARGETS = (
    RewardTarget("channel", SOCIAL_REWARD_CHANNEL_ID, "Канал ZooPark", SOCIAL_REWARD_CHANNEL_URL),
    RewardTarget("chat", SOCIAL_REWARD_CHAT_ID, "Чат ZooPark", SOCIAL_REWARD_CHAT_URL),
)


def target_for_chat(chat_id: int) -> RewardTarget | None:
    return next((target for target in TARGETS if target.chat_id == chat_id), None)


def is_member_status(member: dict) -> bool:
    status = member.get("status")
    if status in {"member", "administrator", "creator"}:
        return True
    return status == "restricted" and bool(member.get("is_member"))


def _membership(session: Session, player: Player, target: RewardTarget) -> SocialMembership:
    membership = session.scalar(
        select(SocialMembership)
        .where(SocialMembership.player_id == player.id, SocialMembership.chat_id == target.chat_id)
        .with_for_update()
    )
    if membership is None:
        membership = SocialMembership(
            player_id=player.id,
            chat_id=target.chat_id,
            target_key=target.key,
            is_member=False,
            reward_amount=SOCIAL_REWARD_AMOUNT,
            checked_at=utcnow(),
        )
        session.add(membership)
        session.flush()
    return membership


def apply_membership(
    session: Session,
    player: Player,
    target: RewardTarget,
    is_member: bool,
) -> int:
    """Apply one membership state transition and return its balance delta."""
    membership = _membership(session, player, target)
    previous = bool(membership.is_member)
    membership.checked_at = utcnow()
    if previous == is_member:
        return 0

    if is_member and not previous:
        # A rejoin starts a fresh reward period at the current campaign amount. A leave
        # always uses the amount stored on the row, so changing the campaign later cannot
        # create or remove an unexpected number of PawCoins.
        membership.reward_amount = SOCIAL_REWARD_AMOUNT

    delta = int(membership.reward_amount) if is_member else -int(membership.reward_amount)
    ledger.grant(
        session,
        player,
        "paw",
        delta,
        "social_subscription_reward",
        ref_table="social_memberships",
        ref_id=membership.id,
        allow_negative=delta < 0,
    )
    membership.is_member = is_member
    return delta


def _payload(session: Session, player: Player) -> dict:
    rows = session.scalars(
        select(SocialMembership).where(SocialMembership.player_id == player.id)
    ).all()
    by_chat = {row.chat_id: row for row in rows}
    return {
        "enabled": True,
        "reward_amount": SOCIAL_REWARD_AMOUNT,
        "paw_coins": ledger.balance(player, "paw"),
        "targets": [
            {
                "key": target.key,
                "title": target.title,
                "url": target.url,
                "reward": int(by_chat[target.chat_id].reward_amount) if target.chat_id in by_chat else SOCIAL_REWARD_AMOUNT,
                "joined": bool(by_chat[target.chat_id].is_member) if target.chat_id in by_chat else False,
            }
            for target in TARGETS
        ],
    }


def sync_player(tg_id: int) -> dict:
    """Ask Telegram for the current state and reconcile both rewards."""
    with get_session() as session:
        player = session.scalar(select(Player).where(Player.telegram_id == tg_id).with_for_update())
        if not player:
            raise HTTPException(404, "Пользователь не найден")
        if player.status == "banned":
            raise HTTPException(403, "Аккаунт заблокирован")

        for target in TARGETS:
            try:
                response = call_bot_api(
                    "getChatMember",
                    {"chat_id": target.chat_id, "user_id": tg_id},
                )
            except TelegramApiError as exc:
                logger.exception("Could not verify %s membership for player %s", target.key, tg_id)
                raise HTTPException(503, f"Не удалось проверить подписку: {target.title}") from exc
            apply_membership(session, player, target, is_member_status(response.get("result") or {}))

        result = _payload(session, player)
        session.commit()
        return result


def handle_membership_update(chat_id: int, user_id: int, is_member: bool) -> None:
    """Apply a Telegram `chat_member` update without making another Bot API call."""
    target = target_for_chat(chat_id)
    if target is None:
        return

    with get_session() as session:
        player = session.scalar(
            select(Player)
            .where(Player.telegram_id == user_id, Player.status == "active")
            .with_for_update()
        )
        if not player:
            return
        apply_membership(session, player, target, is_member)
        session.commit()
