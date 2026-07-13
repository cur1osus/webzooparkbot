from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.db.models import Player, Season, SeasonGate, SeasonPlayer, utcnow
from api.app.zoopark.catalog import SEASON_LENGTH_DAYS


def active_season(session: Session) -> Season:
    # Lock an always-existing singleton before checking for an active row. Without an
    # existing row there is nothing for SELECT ... FOR UPDATE to lock, so two cold-start
    # requests could both create a season and split players between them.
    gate = session.get(SeasonGate, 1, with_for_update=True)
    if gate is None:
        gate = SeasonGate(id=1)
        session.add(gate)
        session.flush()

    now = utcnow()
    season = session.scalars(
        select(Season)
        .where(Season.status == "active", Season.ends_at > now)
        .order_by(Season.starts_at.desc())
        .limit(1)
        .with_for_update()
    ).first()
    if season:
        return season

    expired = session.scalars(
        select(Season).where(Season.status == "active", Season.ends_at <= now).with_for_update()
    ).all()
    for old in expired:
        old.status = "finished"

    season = Season(starts_at=now, ends_at=now + timedelta(days=SEASON_LENGTH_DAYS), status="active")
    session.add(season)
    session.flush()
    return season


def ensure_player_season(session: Session, player: Player) -> Season:
    season = active_season(session)
    if session.get(SeasonPlayer, {"season_id": season.id, "player_id": player.id}) is not None:
        return season

    # A savepoint, not a plain flush: two concurrent requests can both see no membership,
    # and losing that race must not roll back the caller's transaction.
    try:
        with session.begin_nested():
            session.add(SeasonPlayer(season_id=season.id, player_id=player.id))
    except IntegrityError:
        pass
    return season
