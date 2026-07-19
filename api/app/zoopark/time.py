"""Shared Moscow-time boundaries for daily game and economy rotations."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")


def moscow_period_start(now: datetime, reset_hour: int) -> datetime:
    """Return the current period's reset instant as an aware UTC datetime."""
    local_now = now.astimezone(MOSCOW_TIMEZONE)
    start = local_now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    if local_now < start:
        start -= timedelta(days=1)
    return start.astimezone(timezone.utc)


def moscow_period_day(now: datetime, reset_hour: int) -> date:
    """Return the local calendar date on which the current period started."""
    return moscow_period_start(now, reset_hour).astimezone(MOSCOW_TIMEZONE).date()


def next_moscow_reset(now: datetime, reset_hour: int) -> datetime:
    """Return the next reset instant as an aware UTC datetime."""
    local_now = now.astimezone(MOSCOW_TIMEZONE)
    reset = local_now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    if local_now >= reset:
        reset += timedelta(days=1)
    return reset.astimezone(timezone.utc)
