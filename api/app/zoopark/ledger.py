"""The only door through which currency moves.

Nothing outside this module may assign to `player.balance_rub`, `balance_usd` or
`balance_paw`; `test_no_direct_balance_assignment` greps for it. Every movement leaves a
row in `ledger` carrying the reason and the balance it produced, which is what makes an
exploit detectable after the fact instead of merely suspected.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.db.models import LedgerEntry, Player, Treasury, TreasuryLedgerEntry
from api.app.zoopark.catalog import CURRENCIES, Currency

logger = logging.getLogger(__name__)

_BALANCE_ATTR: dict[Currency, str] = {
    "rub": "balance_rub",
    "usd": "balance_usd",
    "paw": "balance_paw",
}

_CURRENCY_LABEL: dict[Currency, str] = {"rub": "₽", "usd": "$", "paw": "🐾"}

Reason = Literal[
    "register",
    "referral_signup",
    "referral_exchange",
    "income_accrual",
    "upkeep",
    "daily_bonus",
    "bank_buy_usd",
    "bank_fee",
    "pack_open",
    "pack_reward",
    "locality_buy",
    "locality_upgrade",
    "merchant_buy",
    "cure_animal",
    "breed",
    "forge_create",
    "forge_upgrade",
    "forge_merge",
    "forge_sell",
    "clan_create",
    "duel_stake",
    "duel_payout",
    "duel_refund",
    "solo_stake",
    "solo_payout",
    "cocktail_reward",
    "safe_prize",
    "transfer_send",
    "transfer_claim",
    "star_payment",
    "star_refund",
    "social_subscription_reward",
    "cosmetic_purchase",
    "development_upgrade",
    "admin_grant",
    "locality_reset_refund",
    "expedition_loot",
    "season_reset",
]

# The house's own reasons. Separate from `Reason`: nothing a player does appears here, and
# nothing here touches a player balance.
TreasuryReason = Literal[
    "bank_fee",
    "safe_prize",
    "admin_adjust",
    "opening_balance",
]


def _log_treasury(
    session: Session,
    currency: Currency,
    delta: int,
    balance_after: int,
    reason: TreasuryReason,
    ref_table: str | None,
    ref_id: int | None,
) -> None:
    session.add(
        TreasuryLedgerEntry(
            currency=currency,
            delta=delta,
            balance_after=balance_after,
            reason=reason,
            ref_table=ref_table,
            ref_id=ref_id,
        )
    )


class InsufficientFunds(HTTPException):
    def __init__(self, currency: Currency, needed: int, available: int) -> None:
        super().__init__(400, f"Недостаточно средств: нужно {needed} {_CURRENCY_LABEL[currency]}, есть {available}")
        self.currency = currency
        self.needed = needed
        self.available = available


def balance(player: Player, currency: Currency) -> int:
    return int(getattr(player, _BALANCE_ATTR[currency]))


def grant(
    session: Session,
    player: Player,
    currency: Currency,
    delta: int,
    reason: Reason,
    *,
    ref_table: str | None = None,
    ref_id: int | None = None,
    allow_negative: bool = False,
) -> int:
    """Move `delta` of `currency` on `player`'s balance and record it. Returns the new balance.

    The caller must already hold a row lock on `player` (`profile.get_player(..., for_update=True)`).
    A negative `delta` that would overdraw raises `InsufficientFunds` unless the caller
    explicitly allows a subscription clawback to create a negative PawCoins balance.
    """
    if currency not in CURRENCIES:
        raise ValueError(f"unknown currency {currency!r}")
    delta = int(delta)
    current = balance(player, currency)
    if delta == 0:
        return current

    new_balance = current + delta
    if new_balance < 0 and not (
        allow_negative and currency == "paw" and reason == "social_subscription_reward"
    ):
        raise InsufficientFunds(currency, -delta, current)

    setattr(player, _BALANCE_ATTR[currency], new_balance)
    session.add(
        LedgerEntry(
            player_id=player.id,
            currency=currency,
            delta=delta,
            balance_after=new_balance,
            reason=reason,
            ref_table=ref_table,
            ref_id=ref_id,
        )
    )
    return new_balance


def spend(
    session: Session,
    player: Player,
    currency: Currency,
    amount: int,
    reason: Reason,
    *,
    ref_table: str | None = None,
    ref_id: int | None = None,
) -> int:
    if amount < 0:
        raise ValueError("spend() takes a non-negative amount")
    return grant(session, player, currency, -amount, reason, ref_table=ref_table, ref_id=ref_id)


def credit_treasury(
    session: Session,
    currency: Currency,
    amount: int,
    reason: TreasuryReason,
    *,
    ref_table: str | None = None,
    ref_id: int | None = None,
) -> int:
    """The house's cut. Locked, because every bank exchange touches the same row."""
    if amount <= 0:
        return treasury_balance(session, currency)
    row = session.get(Treasury, currency, with_for_update=True)
    if row is None:
        row = Treasury(currency=currency, balance=0)
        session.add(row)
        session.flush()
        row = session.get(Treasury, currency, with_for_update=True)
        assert row is not None  # noqa: S101 — just inserted under the same transaction
    row.balance += amount
    _log_treasury(session, currency, amount, int(row.balance), reason, ref_table, ref_id)
    return int(row.balance)


def debit_treasury(
    session: Session,
    currency: Currency,
    amount: int,
    reason: TreasuryReason,
    *,
    ref_table: str | None = None,
    ref_id: int | None = None,
) -> int:
    """Take money back out of the house — currently only the bank safe.

    Returns what was actually taken, which is capped at the balance: the caller decides a
    prize from a balance it read earlier, and an exchange committing in between must not
    be able to drive the treasury negative. The journal records what was taken, not what
    was asked for, so it always reconciles with the row.
    """
    if amount <= 0:
        return 0
    row = session.get(Treasury, currency, with_for_update=True)
    if row is None:
        return 0
    taken = min(int(row.balance), amount)
    if taken <= 0:
        return 0
    row.balance -= taken
    _log_treasury(session, currency, -taken, int(row.balance), reason, ref_table, ref_id)
    return taken


def reconcile_treasury(session: Session, currency: Currency) -> tuple[int, int]:
    """`(journal total, stored balance)` — equal unless something moved the row directly."""
    total = int(
        session.scalar(
            select(func.coalesce(func.sum(TreasuryLedgerEntry.delta), 0)).where(
                TreasuryLedgerEntry.currency == currency
            )
        )
        or 0
    )
    return total, treasury_balance(session, currency)


def treasury_balance(session: Session, currency: Currency) -> int:
    row = session.get(Treasury, currency)
    return int(row.balance) if row else 0


def count_by_reason(
    session: Session,
    player_id: int,
    reason: Reason,
    *,
    since: datetime | None = None,
) -> int:
    """How many ledger movements this player has with the given reason — a monotonic,
    tamper-evident history counter (e.g. the `forge_create` count drives forge price).

    `since` restricts the count to entries at or after that instant, so a counter can be
    anchored to a cutoff rather than to the beginning of time."""
    stmt = select(func.count(LedgerEntry.id)).where(
        LedgerEntry.player_id == player_id,
        LedgerEntry.reason == reason,
    )
    if since is not None:
        stmt = stmt.where(LedgerEntry.created_at >= since)
    return int(session.scalar(stmt) or 0)


def reconcile(session: Session, player_id: int, currency: Currency) -> tuple[int, int]:
    """(sum of every ledger delta, balance actually stored). They must be equal."""
    ledger_total = session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.delta), 0)).where(
            LedgerEntry.player_id == player_id,
            LedgerEntry.currency == currency,
        )
    )
    player = session.get(Player, player_id)
    stored = balance(player, currency) if player else 0
    return int(ledger_total or 0), stored
