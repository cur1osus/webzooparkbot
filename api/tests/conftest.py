"""A real database for every test.

The previous suite mocked `get_session` and asserted on the mock. It could not have
caught a missing unique key, a lost row lock or a ledger that disagreed with a balance,
because none of those live in Python. Here every test runs the actual schema, with
foreign keys switched on.

The engine is in-memory SQLite by default, so a local run stays instant. Set `TEST_DB_URL`
to a MySQL DSN to run the same suite against the engine production actually uses — CI does
both. That is not belt-and-braces: SQLite's `TEXT` is unbounded and MySQL's is 64 KiB, and
four production bugs came out of exactly that gap while the SQLite suite stayed green. One
of them, a rival's turn journal overflowing the column, rolled back the schedule with it
and cost real money in model calls before anyone noticed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

TEST_DB_URL = os.environ.get("TEST_DB_URL", "sqlite://")

os.environ.setdefault("DB_URL", TEST_DB_URL)
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEV_AUTH", "1")
os.environ.setdefault("ALLOWED_TG_IDS", "*")

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import api.app.db.connection as connection  # noqa: E402
from api.app.db.models import Base, Player  # noqa: E402


@pytest.fixture(scope="session")
def _engine():
    """One engine and one schema for the whole run. Building the schema per test is free on
    in-memory SQLite and decidedly not on MySQL, where DDL is neither transactional nor
    cheap — the `db` fixture empties the tables instead."""
    if TEST_DB_URL.startswith("sqlite"):
        engine = create_engine(
            TEST_DB_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
    else:
        engine = create_engine(TEST_DB_URL, pool_pre_ping=True)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db(_engine):
    previous = connection._engine
    connection._engine = _engine
    connection._session_factory.configure(bind=_engine)

    # Emptied child-first, so foreign keys hold throughout and a leftover row can never be
    # what makes the next test pass.
    #
    # The auto-increment counters are deliberately *not* wound back. SQLite reuses ids after
    # a delete and MySQL does not, so a test that assumes "the player is id 1" passes on one
    # engine and fails on the other — but resetting the counters costs a DDL statement per
    # table per test, which took the MySQL run from eleven seconds to six minutes and made it
    # flaky besides. Tests look their ids up instead.
    with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

    from api.app.db.connection import get_session
    from api.app.db.seed import seed_species, seed_treasury

    with get_session() as session:
        seed_species(session)
        seed_treasury(session)
        session.commit()

    yield _engine

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
