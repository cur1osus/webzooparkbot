from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from api.app.db.models import PlayerSeason, Season, User


SEASON_LENGTH_DAYS = 30


def active_season(session: Session) -> Season:
    now = datetime.now(timezone.utc)
    season = (
        session.query(Season)
        .filter(Season.status == "active", Season.ends_at > now)
        .order_by(Season.starts_at.desc())
        .first()
    )
    if season:
        return season

    season = Season(
        starts_at=now,
        ends_at=now + timedelta(days=SEASON_LENGTH_DAYS),
        status="active",
        created_at=now,
    )
    session.add(season)
    session.flush()
    return season


def ensure_player_season(session: Session, user: User) -> Season:
    season = active_season(session)
    player = session.get(PlayerSeason, {"user_id": user.id, "season_id": season.id})
    if player is None:
        session.add(PlayerSeason(user_id=user.id, season_id=season.id, joined_at=datetime.now(timezone.utc)))
        session.flush()
    return season
