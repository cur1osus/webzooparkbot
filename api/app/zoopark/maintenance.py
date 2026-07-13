"""The persisted global technical-break timer."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db.models import GameMaintenance, utcnow

MAINTENANCE_ROW_ID = 1
DEFAULT_MESSAGE = "Технический перерыв"


def _get_row(session: Session, *, for_update: bool = False) -> GameMaintenance:
    stmt = select(GameMaintenance).where(GameMaintenance.id == MAINTENANCE_ROW_ID)
    if for_update:
        stmt = stmt.with_for_update()
    row = session.scalars(stmt).first()
    if row is None:
        row = GameMaintenance(id=MAINTENANCE_ROW_ID, message=DEFAULT_MESSAGE)
        session.add(row)
        session.flush()
    return row


def status(session: Session, now: datetime | None = None) -> dict:
    row = _get_row(session)
    moment = now or utcnow()
    active = row.ends_at is not None and row.ends_at > moment
    return {
        "active": active,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "ends_at": row.ends_at.isoformat() if row.ends_at else None,
        "message": row.message or DEFAULT_MESSAGE,
    }


def start(session: Session, duration_minutes: int, message: str) -> dict:
    now = utcnow()
    row = _get_row(session, for_update=True)
    row.started_at = now
    row.ends_at = now + timedelta(minutes=duration_minutes)
    row.message = message.strip() or DEFAULT_MESSAGE
    row.updated_at = now
    session.flush()
    return status(session, now)


def end(session: Session) -> dict:
    now = utcnow()
    row = _get_row(session, for_update=True)
    row.ends_at = now
    row.updated_at = now
    session.flush()
    return status(session, now)
