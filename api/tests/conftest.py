"""A real database for every test.

The previous suite mocked `get_session` and asserted on the mock. It could not have
caught a missing unique key, a lost row lock or a ledger that disagreed with a balance,
because none of those live in Python. Here every test runs the actual schema in an
in-memory SQLite database, with foreign keys switched on.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("DB_URL", "sqlite://")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEV_AUTH", "1")
os.environ.setdefault("ALLOWED_TG_IDS", "*")

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import api.app.db.connection as connection  # noqa: E402
from api.app.db.models import Base, Player  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    previous = connection._engine
    connection._engine = engine
    connection._session_factory.configure(bind=engine)
    Base.metadata.create_all(engine)

    from api.app.db.connection import get_session
    from api.app.db.seed import seed_species, seed_treasury

    with get_session() as session:
        seed_species(session)
        seed_treasury(session)
        session.commit()

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()
    connection._engine = previous


@pytest.fixture()
def player(db):
    """A registered player with telegram id 1001, holding nothing but the signup dollar."""
    from api.app.schemas.core import RegisterBody
    from api.app.zoopark.core import register

    register(1001, RegisterBody(nickname="tester"))
    return 1001


@pytest.fixture()
def grant():
    """Top up a balance without going through a domain endpoint."""
    from api.app.db.connection import get_session
    from api.app.zoopark import ledger

    def _grant(telegram_id: int, currency: str, amount: int) -> None:
        with get_session() as session:
            row = session.query(Player).filter_by(telegram_id=telegram_id).one()
            ledger.grant(session, row, currency, amount, "daily_bonus")
            session.commit()

    return _grant
